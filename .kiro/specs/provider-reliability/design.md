# Provider Reliability Design — Repository Chat

**Feature**: Multi-Provider LLM Orchestration (Gemini + DeepSeek)  
**Status**: Design Review  
**Owner**: Platform Team  
**Last Updated**: 2024-01-15

---

## Executive Summary

### Problem
Production chat experienced a P0 incident: Gemini API returned `401 UNAUTHENTICATED` due to an incorrect credential type. While the system correctly fell back to Repository Intelligence, there was no secondary LLM provider to attempt before giving up.

### Solution
Make `ProviderManager` production-ready by:
1. **Intelligent retry** — retry transient failures (rate limits, timeouts), skip permanent failures (auth errors)
2. **Automatic fallback** — if primary provider (Gemini) fails, automatically try secondary (DeepSeek)
3. **Zero redundancy** — reuse existing providers, circuit breaker, and streaming safeguards
4. **Enhanced observability** — log provider selection, retry attempts, and fallback reasons per request

### Non-Goals
- Adding new providers (Gemini and DeepSeek already exist)
- Redesigning the pipeline (architecture is already correct)
- Ensemble/hybrid responses (never merge outputs from multiple models)
- AI-driven provider selection (selection is deterministic based on config + circuit state)

### Success Criteria
- **Gemini available** → use Gemini
- **Gemini unavailable** → automatically use DeepSeek
- **Both unavailable** → Repository Intelligence fallback
- User never sees internal provider errors unless all options exhausted
- Every request is traceable through logs with request_id, provider, model, retries, and latency

---

## Current Architecture Audit

### Strengths ✅

1. **Clean separation of concerns**
   - `ProviderManager` orchestrates providers
   - Individual providers (`GeminiProvider`, `DeepSeekProvider`) handle SDK specifics
   - `RetrievalPipeline` consumes `ProviderManager` without knowing implementation details

2. **Circuit breaker already exists**
   - Per-provider circuit with CLOSED/OPEN/HALF_OPEN states
   - Automatically skips OPEN providers
   - Recovery timeout (60s) and half-open testing (10s)

3. **Streaming safeguards already implemented (Phase 9)**
   - If 0 tokens yielded → retry with next provider
   - If tokens already yielded → terminate gracefully, never retry
   - Prevents duplicate/mixed output

4. **Provider-level retry already exists**
   - `GeminiProvider.stream()` retries 3x with exponential backoff (1s → 2s → 4s)
   - `DeepSeekProvider.stream()` retries 2x with exponential backoff (5s → 10s)
   - Both providers handle their own transient failures

5. **Observability foundation**
   - `request_id_var` contextvar for request correlation
   - `PipelineTrace` captures latency, provider_used, tokens_streamed
   - Logs include `exc_info=True` for full tracebacks


### Issues Identified 🔴

1. **Provider-level retry is duplicated**
   - Both `GeminiProvider` and `DeepSeekProvider` implement retry logic independently
   - `ProviderManager` doesn't know about retries → can't log retry attempts
   - When a provider exhausts retries, `ProviderManager` sees it as a single failure
   - **Impact**: Logs don't show "Gemini attempt 1/3" — just "Gemini failed"

2. **No retry strategy differentiation**
   - `GeminiProvider` retries ALL exceptions 3x (including 401 auth errors)
   - `DeepSeekProvider` retries ALL exceptions 2x (including 401 auth errors)
   - **Impact**: Wastes time retrying permanent failures (auth, invalid model)

3. **Circuit breaker threshold is too aggressive**
   - Opens after 3 consecutive failures
   - If Gemini has a bad API key → fails 3 requests → circuit opens for 60s
   - During that 60s, ALL requests skip Gemini and go straight to DeepSeek
   - **Impact**: One config error cascades to affect all users

4. **Logging gaps**
   - No log when circuit breaker skips a provider
   - No log showing which provider was selected at request start
   - `provider_used` is only logged on success, not attempt
   - **Impact**: Hard to diagnose "why did we use DeepSeek instead of Gemini?"

5. **Configuration is implicit**
   - Provider priority is hardcoded: primary=LLM_PROVIDER, secondary=the other one
   - Timeout is hardcoded per provider (Gemini 60s, DeepSeek 120s)
   - No way to disable fallback or configure retry counts
   - **Impact**: Behavior can't be tuned without code changes


---

## Proposed Design

### Principle: Minimal Changes, Maximum Reliability

**Keep:**
- Existing circuit breaker (works correctly)
- Existing streaming safeguards (Phase 9 — works correctly)
- Existing provider interface (`BaseLLMProvider` — no changes)
- Existing provider implementations (Gemini, DeepSeek — small tweaks only)

**Change:**
- **Move retry logic from providers to ProviderManager** — centralize retry policy
- **Add retry classification** — distinguish retryable vs permanent failures
- **Enhance logging** — log provider selection, attempts, and circuit decisions
- **Make config explicit** — add settings for timeouts, retry counts, circuit thresholds

**Do NOT change:**
- Pipeline architecture
- SSE streaming format
- Chat API contract
- Fallback renderer

### Retry Policy Design

#### Retryable Errors (attempt next provider or retry)
- `429 Too Many Requests` — rate limit, wait and retry
- `500 Internal Server Error` — transient server issue
- `502 Bad Gateway` — transient proxy issue
- `503 Service Unavailable` — transient capacity issue
- `504 Gateway Timeout` — transient timeout
- `TimeoutError` / `asyncio.TimeoutError` — network timeout
- `ConnectError` / `ConnectionRefusedError` — transient network

#### Permanent Errors (skip retries, try next provider immediately)
- `401 Unauthorized` — bad API key, do NOT retry
- `403 Forbidden` — bad API key or permissions
- `400 Bad Request` — malformed request (our bug, not transient)
- `404 Not Found` — model doesn't exist
- Any SDK-level authentication exception


#### Retry Strategy

**ProviderManager.stream()** becomes:
```
for each provider in priority order:
    if circuit is OPEN:
        log "skipping {provider} (circuit OPEN)"
        continue
    
    for attempt in 1..max_retries:
        try:
            start streaming
            if first token arrives:
                circuit.record_success()
                return  # success, stop trying other providers
        except Exception as e:
            if is_permanent_error(e):
                log "permanent error, skipping retries"
                break  # skip to next provider
            if attempt < max_retries:
                log "retryable error, attempt {attempt}/{max_retries}"
                await backoff
                continue
            else:
                log "exhausted retries for {provider}"
                break
        
        circuit.record_failure()
        # Try next provider

raise RuntimeError("all providers failed")
```

**Key insight**: Providers no longer retry internally. `ProviderManager` owns the retry loop and can log every attempt.


### Circuit Breaker Tuning

**Current behavior:**
- Opens after 3 consecutive failures
- Recovery timeout: 60s
- Half-open timeout: 10s

**Problem:** Too aggressive for auth errors. If Gemini API key is wrong, circuit opens after 3 requests and stays open for 60s.

**Proposed change:**
- Increase failure threshold to **5 consecutive failures**
- Keep recovery timeout at 60s
- Keep half-open timeout at 10s

**Rationale:**
- Auth errors should be fixed immediately (not after 3 requests)
- Transient issues (rate limits, timeouts) benefit from circuit breaker
- Higher threshold prevents one-off network glitches from opening circuit

**Alternative considered:** Separate thresholds for auth vs transient failures. **Rejected** — adds complexity, no clear benefit.


### Configuration Design

#### Current (implicit)
```python
# Hardcoded in ProviderManager._load_from_settings()
entries.append(ProviderEntry(
    name=provider_name,
    provider=primary,
    priority=1,
    timeout=60.0,  # hardcoded
))
```

#### Proposed (explicit settings)

**Add to `backend/settings.py`:**
```python
# LLM Provider Reliability Settings
llm_timeout_seconds: int = Field(60, alias="LLM_TIMEOUT_SECONDS")
llm_max_retries: int = Field(3, alias="LLM_MAX_RETRIES")
llm_retry_delay_seconds: float = Field(1.0, alias="LLM_RETRY_DELAY_SECONDS")
llm_circuit_failure_threshold: int = Field(5, alias="LLM_CIRCUIT_FAILURE_THRESHOLD")
llm_circuit_recovery_seconds: float = Field(60.0, alias="LLM_CIRCUIT_RECOVERY_SECONDS")
```

**Add to `.env.example`:**
```bash
# LLM Reliability (optional — defaults are production-ready)
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=3
LLM_RETRY_DELAY_SECONDS=1.0
LLM_CIRCUIT_FAILURE_THRESHOLD=5
LLM_CIRCUIT_RECOVERY_SECONDS=60.0
```

**Rationale:**
- **Configurable but not required** — defaults are sensible
- **Single config for all providers** — avoids per-provider tuning complexity
- **Environment-specific tuning** — prod can use different values than dev

**Alternative considered:** Per-provider timeouts/retries. **Rejected** — adds 6+ config vars, no clear use case.


### Logging Design

#### Per-Request Trace

**On request start:**
```
INFO [ProviderManager] provider_selection provider=gemini priority=1 circuit_state=closed request_id=abc123
```

**On retry attempt:**
```
WARNING [ProviderManager] provider_retry provider=gemini attempt=2/3 error_type=TimeoutError retryable=true delay=2.0s request_id=abc123
```

**On permanent error:**
```
ERROR [ProviderManager] provider_permanent_error provider=gemini error_type=ClientError code=401 retryable=false request_id=abc123
```

**On circuit skip:**
```
INFO [ProviderManager] provider_skipped provider=gemini reason=circuit_open circuit_failure_count=5 request_id=abc123
```

**On success:**
```
INFO [ProviderManager] provider_success provider=gemini model=gemini-2.5-flash attempt=1 tokens=247 latency_ms=1834 request_id=abc123
```

**On fallback to next provider:**
```
WARNING [ProviderManager] provider_fallback from=gemini to=deepseek reason=retries_exhausted request_id=abc123
```

**On all providers failed:**
```
ERROR [ProviderManager] all_providers_failed tried=[gemini,deepseek] request_id=abc123
```


#### Structured Logging Fields

All provider logs should include:
- `request_id` (from contextvar)
- `provider` (gemini / deepseek)
- `model` (gemini-2.5-flash / deepseek-ai/deepseek-v4-flash)
- `attempt` (1, 2, 3)
- `error_type` (TimeoutError, ClientError, etc.)
- `retryable` (true/false)
- `circuit_state` (closed/open/half_open)
- `latency_ms` (on success)
- `tokens` (on success, if streaming)

#### Secret Sanitization

**Never log:**
- API keys (even prefixes)
- Full error messages that might contain keys
- Request/response bodies

**Do log:**
- HTTP status codes (401, 429, etc.)
- Error types (`ClientError`, `TimeoutError`)
- Provider/model names


---

## Files to Modify

### 1. `backend/settings.py` (ADD config fields)
**Why:** Make reliability settings explicit and configurable  
**Risk:** Low — new fields with defaults, no breaking changes  
**Changes:**
- Add 5 new fields: `llm_timeout_seconds`, `llm_max_retries`, `llm_retry_delay_seconds`, `llm_circuit_failure_threshold`, `llm_circuit_recovery_seconds`
- All have sensible defaults

### 2. `.env.example` (ADD config documentation)
**Why:** Document new settings for operators  
**Risk:** None — documentation only  
**Changes:**
- Add commented section explaining reliability settings

### 3. `services/chat/provider_manager.py` (MAJOR refactor)
**Why:** Implement smart retry and enhanced logging  
**Risk:** Medium — core orchestration logic  
**Changes:**
- Extract `_is_retryable_error()` helper
- Move retry loop from providers into `stream()` and `generate()`
- Add structured logging at every decision point
- Read retry/timeout config from settings
- Pass config to CircuitBreaker constructor

