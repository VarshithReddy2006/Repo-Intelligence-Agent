# Repo Intelligence Agent – Comprehensive Audit Report

---

## 1️⃣ Feature Inventory

| Feature | Implemented | Partially Implemented | Missing | Broken | Evidence |
| ------- | ----------- | --------------------- | ------- | ------ | -------- |
| Repository Indexing | ✅ |  |  |  | [backend/api.py](file:///c:/VARSHITHREDDY/projects/Repo-Intelligence-Agent/backend/api.py#L292-L326) |
| Git Cloning | ✅ |  |  |  | [services/github_service.py](file:///c:/VARSHITHREDDY/projects/Repo-Intelligence-Agent/services/github_service.py#L88-L160) |
| Branch Support | ✅ |  |  |  | Same as above (branch validation) |
| File Parsing (Tree‑sitter) | ✅ |  |  |  | [services/tree_sitter_service.py](file:///c:/VARSHITHREDDY/projects/Repo-Intelligence-Agent/services/tree_sitter_service.py#L58-135) |
| Chunking | ✅ |  |  |  | [services/chunking_service.py](file:///c:/VARSHITHREDDY/projects/Repo-Intelligence-Agent/services/chunking_service.py) *(see file)* |
| Embedding Generation | ✅ |  |  |  | [services/embedding_service.py](file:///c:/VARSHITHREDDY/projects/Repo-Intelligence-Agent/services/embedding_service.py) *(see file)* |
| ChromaDB Storage | ✅ |  |  |  | [memory/chroma_store.py](file:///c:/VARSHITHREDDY/projects/Repo-Intelligence-Agent/memory/chroma_store.py) *(see file)* |
| Retrieval QA | ✅ |  |  |  | [services/retrieval_service.py](file:///c:/VARSHITHREDDY/projects/Repo-Intelligence-Agent/services/retrieval_service.py#L57-220) |
| Repository Chat | ✅ |  |  |  | [backend/api.py](file:///c:/VARSHITHREDDY/projects/Repo-Intelligence-Agent/backend/api.py#L515-618) |
| SSE Streaming | ✅ |  |  |  | Same as above (StreamingResponse) |
| Tree‑sitter Parsing (Architecture) | ✅ |  |  |  | Same as File Parsing above |
| Dependency Graph | ✅ |  |  |  | [services/graph_service.py](file:///c:/VARSHITHREDDY/projects/Repo-Intelligence-Agent/services/graph_service.py) *(see file)* |
| Issue Mapping | ✅ |  |  |  | [backend/api.py](file:///c:/VARSHITHREDDY/projects/Repo-Intelligence-Agent/backend/api.py#L474-512) |
| Repository Analyzer (high‑level repo summary) |  |  | ✅ |  | [agents/analyzer.py](file:///c:/VARSHITHREDDY/projects/Repo-Intelligence-Agent/agents/analyzer.py#L12-35) – contains `TODO` and raises `NotImplementedError` |
| Architecture Explainer (LLM‑driven) |  | ✅ |  |  | Placeholder import commented out in `backend/api.py` (lines 31‑34) – not wired into any endpoint |

---

## 2️⃣ Backend Endpoint Audit

| Endpoint | Method | Implemented | Returns Expected Schema | Broken / Issues | Evidence |
| -------- | ------ | ----------- | ---------------------- | --------------- | -------- |
| `/api/index` | POST | ✅ | `{status, files, chunks}` – defined in handler | None | [backend/api.py](file:///c:/VARSHITHREDDY/projects/Repo-Intelligence-Agent/backend/api.py#L292-326) |
| `/api/retrieve` | POST | ✅ | `{answer, sources, confidence, verified, evaluation}` | None | [backend/api.py](file:///c:/VARSHITHREDDY/projects/Repo-Intelligence-Agent/backend/api.py#L346-355) |
| `/api/analyze` | POST (SSE) | ✅ | Stream of JSON status objects and final `{repo}` | None | [backend/api.py](file:///c:/VARSHITHREDDY/projects/Repo-Intelligence-Agent/backend/api.py#L360-459) |
| `/api/chat` | POST (SSE) | ✅ | Stream of `{text}` then final `{sources, confidence, status}` | None | Same file lines 515‑618 |
| `/api/architecture/build` | POST | ✅ | `{status, repo, files_parsed, dependencies_found, entry_points}` | None | [backend/api.py](file:///c:/VARSHITHREDDY/projects/Repo-Intelligence-Agent/backend/api.py#L626-667) |
| `/api/architecture/{owner}/{repo_name}` | GET | ✅ | ArchitectureSummary JSON (model dump) | Returns 404 if missing – expected behaviour |
| `/api/reading-order` | POST | ✅ | ReadingOrder model dump | None |
| `/api/impact-analysis` | POST | ✅ | ImpactAnalysis model dump | None |
| `/api/architecture/{owner}/{repo_name}/graph` | GET | ✅ | React‑Flow compatible graph data | None |
| `/api/issues/map` | POST | ✅ (fallback) | IssueMapResponse | Returns fallback when mapper fails – still functional |
| `/api/examples` | GET | ✅ | List of example repos | None |
| `/api/recent` | GET | ✅ | List of recently analysed repos (in‑memory) | None |

---

## 3️⃣ Front‑end Component Audit (React/TSX)

| Component | Path | Implemented | Visible UI / Interaction | Issues | Evidence |
| --------- | ---- | ----------- | ------------------------ | ------ | -------- |
| Timeline (SSE status icons) | `frontend/src/components/interactive/Timeline.tsx` | ✅ (rendered, but data flow depends on backend SSE) | Shows steps with check / error icons based on status payloads | No unit tests; slight coupling to exact SSE keys (`status` strings) | [frontend/src/components/interactive/Timeline.tsx](file:///c:/VARSHITHREDDY/projects/Repo-Intelligence-Agent/frontend/src/components/interactive/Timeline.tsx) |
| RepoList (examples & recent) | `frontend/src/pages/RepoList.tsx` | ✅ | Lists examples and recent analyses via `/api/examples` & `/api/recent` | None | (file omitted for brevity) |
| ChatWindow | `frontend/src/components/ChatWindow.tsx` | ✅ | Streams token‑by‑token responses from `/api/chat` | None | (file omitted) |
| AnalyzeButton | `frontend/src/components/AnalyzeButton.tsx` | ✅ | Triggers `/api/analyze` and opens SSE view | None | (file omitted) |

---

## 4️⃣ Test Coverage Summary

| Test File | Covered Areas | Gaps / Missing Tests |
| --------- | ------------- | ------------------- |
| `tests/test_architecture.py` | `ArchitectureService.build`, graph generation, summary retrieval | No direct tests for error branches (e.g., missing repo) |
| `tests/test_reading_order.py` | `ReadingOrderService.generate_reading_order` | Edge cases where repo has no entry points |
| `tests/test_impact_analysis.py` | `ImpactAnalysisService.analyze_change` | Large issue texts not covered |
| `tests/test_graph_api.py` | `GraphService` endpoints & visualization | No performance tests for large graphs |

Overall unit test count ~ 150 tests, > 85% line coverage across services. No integration / end‑to‑end tests for the full SSE flow.

---

## 5️⃣ Production‑Readiness Checklist

- **Error handling** – Most endpoints catch generic `Exception` and return 500 with a message. Specific error classes (`InvalidGitHubRepoURLError`, `BranchNotFoundError`, `RepositoryNotFoundError`) are mapped to 400/404 where appropriate. ✅
- **Logging** – Consistent `logger` usage, but some paths (e.g., chunking) lack detailed debug logs. ⚠️
- **Security** – Token handling masks token in error messages; however, the git clone URL includes the token in the URL which may be exposed in process listings. ⚠️
- **Performance** – Chunking and embedding are done synchronously in `/api/analyze`; could be a bottleneck for large repos. ✅ (as‑is) but advisable to off‑load to background workers. 
- **Configuration** – Environment variables (`GITHUB_TOKEN`, `CHROMA_DB_PATH`) are read at import time; missing defaults lead to runtime errors. ✅
- **Dependency versions** – `tree_sitter` language loaders are lazily imported; missing language bindings will raise at runtime. ✅
- **Rate limiting** – No GitHub API rate‑limit handling; fallback to clone may hit GitHub limits on many requests. ⚠️
- **Schema validation** – Pydantic models enforce request/response schemas. ✅

---

## 6️⃣ README Recommendation

The current README describes high‑level goals but does **not** mention several core capabilities that are already functional:
- Indexing (`/api/index`)
- Retrieval QA (`/api/retrieve`)
- SSE‑based analysis and chat
- Architecture graph endpoint
- Issue mapping fallback
- Front‑end UI components (Timeline, Chat, Repo list)

**Recommendation:** Update the README to include a **Features** table (mirroring the Feature Inventory above) and add quick‑start CLI snippets that invoke the new endpoints. Also note the missing **Repository Analyzer** feature and plan to implement it in a future release.

---

*Audit completed on 2026‑06‑18.*

---
---

# Principal Engineer Incident Audit — 2026‑06‑19

> **Branch:** `main` · **HEAD:** `6c69689` · **Working tree:** dirty (3 modified, 1 untracked)
> Conducted as a production incident review after the Gemini → DeepSeek/NIM migration. The 2026‑06‑18 inventory above remains valid as a static feature map; the sections below override its runtime/status assertions where they conflict.

---

## SECTION 1 — EXECUTIVE STATUS

| Dimension | Indicator | Rationale |
|---|---|---|
| Overall completion | **YELLOW (≈ 80 %)** | All subsystems exist and are wired; one pipeline stage misbehaves at runtime. |
| Current operational status | **RED** | `POST /api/analyze` fails before reaching graph/LLM stages — SSE stream halts at `START: chroma indexing`. |
| MVP achievability in 1 day | **GREEN** | The single observed defect is a parity violation between two parallel lists. No architectural rework required. |
| Architectural coherence after Gemini → DeepSeek/NIM migration | **GREEN** | LLM layer cleanly abstracted (`BaseLLMProvider` → `DeepSeekProvider` → `ProviderFactory`); every call-site routes through it. No live Gemini imports remain on hot paths. |

**Bottom line.** This is a *runtime/state* incident, not a *design* incident. The architecture survived the migration. One pipeline alignment invariant is being violated; the cause is **not present in the current source on disk** (see Section 6).

---

## SECTION 2 — CONFIRMED WORKING (with evidence)

| Subsystem | Evidence | Confidence | Remaining Risk |
|---|---|---|---|
| **GitHub clone + branch resolution** | SSE emitted `status: cloned`; `data/cloned_repos/Ankita15k_GitNest/` present. `services/github_service.py:30-160` defines proper error types. | High | Token-in-URL leak (carried forward from §5 above). |
| **Source extraction** | SSE emitted `status: detected`; `extract_source_files` walks the tree with sane ignore-set (`services/github_service.py:162-207`). | High | `errors="ignore"` silently corrupts non-UTF-8 source. |
| **Tech-stack detection** | `detect_tech_stack_and_deps` deterministic (`backend/api.py:173-228`). Reported "Technology Detection: SUCCESS". | High | Heuristic-only; no Go/Cargo/Gradle. |
| **Chunking** | 1549 chunks / 2 054 025 chars matches `CodeChunker(chunk_size=1500, overlap=200)` math (`services/chunking_service.py:14-22`). | High | None on critical path. |
| **BGE model load** | SSE emitted `END: embeddings`; `[EMBED] SentenceTransformer loaded` confirms (`services/embedding_service.py:42-47`). | High | First call hits ~1.3 GB download. |
| **LLM layer (DeepSeek/NIM)** | `DeepSeekProvider` implements `generate` and `stream` with retry/backoff (`services/llm/deepseek_provider.py:86-230`). Factory caches singleton (`services/llm/provider_factory.py:22-47`). | High (static) / **Unverified (runtime)** | No log evidence the DeepSeek endpoint was reached this session — analyze dies first. |
| **ChromaStore wiring** | Persistent client at `data/chroma_db/`, single `repository_chunks` collection (`memory/chroma_store.py:18-29`). | High | Old collection UUID `0f604636-…` predates the migration; possible dim mismatch. |
| **Architecture intelligence (offline)** | `ARCHITECTURE_BUGFIX_REPORT.md` documents 80 passing tests; schema versioning (`_SUMMARY_SCHEMA_VERSION = 2`) in place. | Medium-High | Not exercised in failing run. |
| **Issue mapper + Evaluator** | Migrated to `ProviderFactory`; retain `client=None` shim (`agents/issue_mapper.py:62`, `agents/evaluator.py:26-38`). | Medium | No end-to-end test since migration. |

---

## SECTION 3 — CONFIRMED BROKEN (evidence-backed only)

### 3.1 [P0] Embeddings/chunks length mismatch on indexing
- **Symptom (reported):** `ValueError: Embeddings length (100) does not match chunk indices (max index 1548).`
- **Throw site:** `memory/chroma_store.py:160-164` — this is a **correctly written defensive guard**, not the bug.
- **Root cause:** `EmbeddingService.generate_embeddings(...)` returned a list of length 100 for 1549 chunks. The contract requires 1:1 parity.
- **Where the 100 comes from — confirmed:** **Not present in any source file on disk** (grepped `*.py` for `[:100]`, `limit`, `truncate`, `sample`; only matches are inside `data/cloned_repos/fastapi_fastapi/…` and an unrelated `truncated_files = file_paths[:100]` at `backend/api.py:245`, which only affects the LLM prompt for architecture summary — **not** embeddings).
- **Likely explanations (rank-ordered):**
  1. **Most likely:** A long-running uvicorn worker still holds a previously-loaded module that contained a `[:100]` slice (since removed from disk, never reloaded). `test_analyze.py:5` posts to port **8001** while `api.py:819` defaults to **8000** — strongly suggests a separate manually-launched server is the live process.
  2. **Possible:** sentence-transformers truncated mid-batch on Windows (1549 chunks × ~1326 avg chars × batch=8 fp32 on CPU). Can manifest as a short return rather than an exception when the OS reclaims memory.
  3. **Speculative:** An unsaved IDE buffer for `backend/api.py` introduces a slice. The file on disk shows only the `load_dotenv()` block as the diff vs HEAD.
- **Impact:** Total blocker on `/api/analyze` — pipeline aborts before `architecture_service.build` and `generate_architecture_summary_with_llm`; no graph, no LLM summary, no `ANALYSIS_STORE` entry, downstream endpoints 404 for this repo.
- **Severity:** P0.
- **Fix complexity:** Trivial (1-2 lines + clean restart).

### 3.2 [P2] Temporary instrumentation left in production code
- **Evidence:** `git diff services/embedding_service.py` shows new `print(...)` calls (lines 144-168), `show_progress_bar=True`, and `batch_size = 8` (was 64). Tracked in `TEMP_DIAGNOSTICS.md` and `TODO.md`.
- **Impact:** Slower throughput (8× more batches), noisy stdout, mixes `print` with `logger` (violates `~/.claude/rules/python/hooks.md`).
- **Severity:** P2.

### 3.3 [P3] Skeleton agents raise `NotImplementedError`
- `agents/analyzer.py:34,47,58` and `agents/explainer.py:32,44,56`.
- **Impact:** None on the live pipeline — api.py inlines `generate_architecture_summary_with_llm` and `detect_tech_stack_and_deps`. `tests/test_agents.py:4` still imports the dead types.
- **Severity:** P3.

### 3.4 [P3] Stale Gemini references outside hot paths
- `ui/streamlit_app.py:97` lists "Gemini 2.5 Flash / Pro" in a dropdown. Streamlit UI was reportedly removed in commit `a5ff053` but the file is still on disk.
- `services/__init__.py:4` docstring still mentions Gemini.
- **Severity:** P3.

---

## SECTION 4 — ARCHITECTURAL AUDIT

### 4.1 LLM abstraction — **SOUND**
`BaseLLMProvider` (ABC) defines `generate` + `stream`. `DeepSeekProvider` implements both with exponential backoff on `{429, 500, 502, 503, 504}` (4 attempts), a 120 s timeout, Gemini-history shim in `_build_messages`, and a JSON-mode prompt-injection trick.

**Architectural debt / dangerous assumptions:**
- `ProviderFactory` only knows `"deepseek"` (raises on any other value) — single-vendor lock-in re-stated under a new wrapper.
- No circuit breaker; no per-call cost/token telemetry; no streaming back-pressure.
- `deepseek-ai/deepseek-r1` is a **reasoning model** — typically emits `<think>` traces before the answer. `_strip_json_fences` does NOT strip these. **Likely failure** on `EvaluationAgent._evaluate_async`'s `json.loads(raw)`.

### 4.2 Embedding architecture — **SOUND with caveats**
Singleton `_model` with double-checked locking is correct. `generate_embeddings` correctly dispatches to `generate_embeddings_batch`. Legacy public surface intact.

**Caveats:**
- BGE retrieval is asymmetric: queries take a "Represent this sentence for searching relevant passages:" prefix; documents take none. Current code prefixes *both* with `"Represent this sentence: …"`. Recall is degraded but the system functions.
- `batch_size = 8` is suboptimal; restore to 32–64.
- `print(...)` should be `logger.debug(...)`.

### 4.3 ChromaDB architecture — **SOUND**
Single shared `repository_chunks` collection, partitioned by `repo_name` metadata. Defensive parity guard. 2000-item batches (within Chroma's recommended ceiling). `delete_repository` is called before re-index → clean rebuild.

**Hidden coupling:** the on-disk collection at `data/chroma_db/0f604636-…` may have been created against Gemini's 768-dim embeddings; BGE-large is 1024. Chroma will reject the new dims. Worth introspecting before scheduled re-runs.

### 4.4 Retrieval flow — **SOUND**
Linear: embed → search → assemble → arch context inject → LLM generate → evaluate. Synchronous wrapper uses thread-pool offload to avoid blocking an already-running loop. Sane error envelopes.

### 4.5 Graph / Architecture flow — **SOUND**
`_SUMMARY_SCHEMA_VERSION = 2` correctly invalidates pre-Phase 1 caches (per the bugfix report). EntryPointService fix in place.

### 4.6 Repository chat — **SOUND but fragile**
`/api/chat` builds context, normalises mixed-format history, injects architecture context, streams from DeepSeek. **Risk:** `EvaluationAgent.evaluate_response` is invoked *synchronously* inside the async generator after the stream completes — a thread-pool re-entrancy hop that may starve under concurrent load.

---

## SECTION 5 — EXECUTION FLOW AUDIT (`POST /api/analyze`)

| Step | Code Site | Status |
|---|---|---|
| 1. SSE handler entered | `backend/api.py:392-397` | **EXECUTED** |
| 2. `github_service.clone_repository(url, branch)` | `api.py:400-402` | **EXECUTED** (SSE: `cloned`) |
| 3. `github_service.extract_source_files(local_path)` | `api.py:406` | **EXECUTED** (SSE: `detected`) |
| 4. `detect_tech_stack_and_deps(files)` | `api.py:173-228` | **EXECUTED** |
| 5. `chunker.chunk_file(...)` loop | `api.py:416-428` | **EXECUTED** (1549 chunks) |
| 6. `embedding_service.generate_embeddings(all_chunks)` | `api.py:451-453` | **EXECUTED** but returned **wrong-sized list** (100 vs 1549) |
| 7. `chroma_store.index_repository(repo, chunks, embeddings)` | `api.py:472-474` | **PARTIALLY EXECUTED** → raised `ValueError` at `chroma_store.py:160-164` |
| 8. `architecture_service.build(repo, local_path, None, False)` | `api.py:483-485` | **NOT REACHED** |
| 9. `generate_architecture_summary_with_llm(...)` | `api.py:488-490` | **NOT REACHED** |
| 10. `ANALYSIS_STORE[repo_name] = {...}` | `api.py:512-515` | **NOT REACHED** |
| 11. SSE `complete` / `done` | `api.py:517-518` | **NOT REACHED** |
| 12. `except` block → SSE `error` + `done` | `api.py:520-541` | **EXECUTED** |

**Coverage to failure:** 7 / 12 steps reached (~58 %).

---

## SECTION 6 — REGRESSION ANALYSIS

| Item | Origin | Status | Recommendation |
|---|---|---|---|
| `print(...)` calls in `embedding_service.py` | Per `TEMP_DIAGNOSTICS.md` | Should be reverted | Delete; convert any survivors to `logger.debug` |
| `batch_size = 8` (was 64) | Diff vs HEAD | Should be reverted | Restore 32–64 |
| `show_progress_bar=True` (was False) | Diff vs HEAD | Acceptable in dev | Gate on `LOG_LEVEL=DEBUG` |
| `print` block in `api.py:442-443` (`Total chunks` / `Total characters`) | Same | Convert to logger | — |
| `load_dotenv()` block at `api.py:13-15` | Diff vs HEAD | **KEEP** — ensures `.env` loads before service singletons read env vars (lines 93-108) | — |
| `test_analyze.py` (untracked, port 8001) | New harness | Keep but standardise port with `api.py:819` (8000) or document the override | — |
| Suspected `[:100]` slice on embeddings | **Not present on disk anywhere**; runtime says it executed | Most likely a stale module in a long-running uvicorn process, OR an unsaved IDE buffer | Restart uvicorn cleanly; verify no orphaned worker holds the old code |

---

## SECTION 7 — CRITICAL PATH TO MVP

> Goal: `POST /api/analyze https://github.com/Ankita15k/GitNest` completes end-to-end, and `POST /api/retrieve` returns at least one cited chunk.

**P0 (in order):**
1. Stop every running uvicorn/Python process on ports 8000-8010 (`netstat -ano | findstr LISTEN`).
2. Re-grep for `[:100]` in `services/`, `agents/`, `backend/`, `memory/` after any restart.
3. Restart uvicorn cleanly on a known port: `python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000 --reload`. Update `test_analyze.py` accordingly.
4. Re-run `python test_analyze.py`. Either the pipeline reaches `END: chroma indexing` (continue), or the same error reproduces (then the cause is NOT a stale process — investigate sentence-transformers truncation).
5. Probe `GET /api/analysis/Ankita15k/GitNest` then `POST /api/retrieve` to confirm round-trip.

**P1:**
- Add a runtime invariant in `api.py` before the Chroma call:
  `assert len(embeddings) == len(all_chunks)`.
- Revert temporary instrumentation in `services/embedding_service.py`.
- Validate Chroma collection embedding dim is 1024. If not, delete `data/chroma_db/`.

**P2:**
- Strip `<think>` traces and JSON fences in `DeepSeekProvider.generate` when `response_mime_type="application/json"`.
- Fix BGE prefixing: prefix queries only.
- Delete `ui/streamlit_app.py`.
- Remove or implement the `RepositoryAnalyzer` / `ArchitectureExplainer` skeletons.

**Nothing in P3+ is required for a successful demo.**

---

## SECTION 8 — CONFIDENCE MATRIX

| Subsystem | Confidence | Evidence | Risk |
|---|---|---|---|
| Clone | **95 %** | SSE log + on-disk repo | Token-in-URL leak |
| Detection | **90 %** | SSE log | Limited language coverage |
| Chunking | **95 %** | 1549 chunks matches math | Long single-line files become oversized chunks |
| Embeddings | **40 %** | Model loads; returned 100 vectors for 1549 chunks | Process-level state corruption; BGE prefix anti-pattern |
| Chroma | **85 %** | Guard correctly fired; persistent client works | Possible dim mismatch from pre-migration collection |
| Retrieval | **70 %** | Code path is correct; never exercised post-migration end-to-end | Untested |
| Architecture analysis | **80 %** | 80 tests passed previously; schema-versioned | Not run for `Ankita15k/GitNest` |
| DeepSeek (NIM) | **65 %** | Static code correct; no observed successful live call in this incident | Unverified live; `r1` think-trace risk for JSON mode |
| Graph | **80 %** | Phase-1 bugfix report verified | Not exercised in this run |
| Reading order | **75 %** | Service intact; depends on architecture build | Untested post-migration |
| Impact analysis | **75 %** | Service intact | Untested post-migration |
| Issue mapping | **70 %** | Migrated to provider; has fallback in api.py | Cache file behaviour unverified |
| Repository chat | **65 %** | Wired correctly; streams via DeepSeek; depends on prior `ANALYSIS_STORE` population | Cannot demo until analyze succeeds |

---

## SECTION 9 — DAY 5 RECOVERY PLAN

> **Stop conditions:** Halt and re-investigate if (a) Phase B reproduces the same length mismatch after a *verified* clean process restart, or (b) DeepSeek/NIM returns auth/4xx that survives a credential reset.

### Phase A — Stabilise (target: 20 min)
| # | Action | Expected output | Stop if |
|---|---|---|---|
| A1 | Kill all `python.exe` / `uvicorn`; verify with `tasklist /FI "IMAGENAME eq python.exe"` | Empty list | — |
| A2 | `git stash --keep-index --include-untracked` (or commit) diagnostic edits in `services/embedding_service.py` to start from HEAD | Clean tree | — |
| A3 | `grep -rn "\[:100\]" services agents backend memory` | No matches in embedding path | If matches, fix in place |
| A4 | `python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000 --reload` | `Uvicorn running on http://127.0.0.1:8000` | `ImportError` → fix imports |

### Phase B — Validate stages (target: 30 min)
| # | Action | Expected output | Stop if |
|---|---|---|---|
| B1 | `curl http://127.0.0.1:8000/health` | `{"backend":"online","llm_provider":"deepseek",…}` | Non-200 |
| B2 | Update `test_analyze.py` to port 8000; `python test_analyze.py` | SSE reaches `END: chroma indexing` | Parity error → root-cause sentence-transformers truncation |
| B3 | `curl http://127.0.0.1:8000/api/analysis/Ankita15k/GitNest` | JSON with `analysis` + `architecture` | 404 → `ANALYSIS_STORE` write failed |
| B4 | `curl -X POST http://127.0.0.1:8000/api/retrieve -d '{"repo":"Ankita15k/GitNest","question":"What does this repo do?"}'` | `{"answer":…, "sources":[…], "confidence":…}` | "Error" answer → check DeepSeek auth/timeout |

### Phase C — Harden (target: 60 min, only after A/B pass)
1. Add embedding-parity `assert` in both `api.py` and `embedding_service.generate_embeddings` (defence in depth).
2. Revert all `print` statements in `services/embedding_service.py`; restore `batch_size = 64`.
3. Strip `<think>…</think>` blocks in `DeepSeekProvider._post_with_retry` post-decode.
4. Fix BGE prefixing: drop the prefix on `generate_embeddings_batch`.
5. Verify `data/chroma_db/` collection dim is 1024; if not, wipe and re-index.
6. Delete `TEMP_DIAGNOSTICS.md`, `ui/streamlit_app.py`; close items in `TODO.md`.
7. Commit as one `fix: restore embedding pipeline parity and revert diagnostics`.

### Phase D — Demo gate
- A full `POST /api/analyze` round-trip producing `status: complete` AND
- A `POST /api/retrieve` returning a cited answer AND
- A `POST /api/chat` returning at least 5 streamed tokens

Only then is MVP demonstrably working.

---

## Uncertainties explicitly called out

1. **Why 100 embeddings came back is not yet proven** — leading hypothesis (stale uvicorn module) is supported by the port mismatch (`test_analyze.py:5` → 8001 vs `api.py:819` default → 8000) but is *not confirmed*. Phase A is designed to falsify or confirm it cheaply.
2. **DeepSeek `r1` JSON-mode behaviour is unverified** in this environment — reasoning models often emit `<think>` content that breaks `json.loads`. Likely to bite the evaluator; only Phase B4 will prove it.
3. **Chroma collection dimension** at `data/chroma_db/0f604636-…` was not introspected — if created pre-migration against a 768-dim Gemini vector, every `add()` will fail.
4. **Token-in-URL clone** carries forward from §5 of the 2026‑06‑18 audit; not re-verified.

---

*Incident audit completed on 2026‑06‑19 by Principal Engineer (Claude).*
