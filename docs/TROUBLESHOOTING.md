# Troubleshooting Guide

Common issues encountered when running the Repo Intelligence Agent, with resolution steps.

---

## LLM Provider Authentication Failures

### Symptom

Startup log contains:
```
ERROR backend.startup: LLM_PROVIDER_HEALTH provider=gemini healthy=false error_type=invalid_credential_type
```
Chat requests always fall back to the FallbackRenderer. `GET /api/chat/health` returns `"authenticated": false`.

### Root Cause

The Gemini provider validates credentials at startup by listing available models. If the key is an OAuth token, a service account credential, or an Application Default Credential instead of a Google AI Studio Developer API key, the SDK returns `401 UNAUTHENTICATED ACCESS_TOKEN_TYPE_UNSUPPORTED`.

### Solution

1. Get a valid API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Set `GEMINI_API_KEY=AIza...` in your `.env` (must start with `AIza`)
3. Either restart the server or call `POST /api/chat/reload` to reload without restarting

For DeepSeek, verify your NVIDIA NIM key at [build.nvidia.com](https://build.nvidia.com) and set `DEEPSEEK_API_KEY=nvapi-...`.

---

## HuggingFace Model Download Failures

### Symptom

On first startup, the process hangs or throws a network error during BGE model download.

### Root Cause

`SentenceTransformer` downloads `BAAI/bge-small-en-v1.5` (~130 MB) from HuggingFace on first use. Network restrictions or rate limits can interrupt this.

### Solution

Pre-download the model manually with your virtual environment active:

```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"
```

If you encounter rate limiting, set a HuggingFace access token:

```bash
# Windows PowerShell
$env:HF_TOKEN="your_huggingface_token"

# macOS / Linux
export HF_TOKEN="your_huggingface_token"
```

---

## ChromaDB Dimension Mismatch

### Symptom

`POST /api/index` or `POST /api/analyze` raises:
```
ValueError: Collection dimension mismatch
```
or
```
IndexError: dimension of input vector does not match
```

### Root Cause

The ChromaDB collection was created with a different embedding model (e.g., 768-dimensional Gemini embeddings) but the current model produces 384-dimensional BGE vectors.

### Solution

Delete the Chroma database directory and re-analyze. This wipes all cached vectors.

**Windows (PowerShell):**
```powershell
Remove-Item -Recurse -Force data/chroma_db
```

**macOS / Linux:**
```bash
rm -rf data/chroma_db
```

ChromaDB will recreate the directory on the next analysis request.

---

## Uvicorn Keeps Reloading During Analysis

### Symptom

The backend restarts itself repeatedly while `POST /api/analyze` is running. Analysis never completes.

### Root Cause

`CLONED_REPOS_PATH` is set to a path inside the project directory (default is `data/cloned_repos`). When repositories are cloned, WatchFiles detects new files being written to `data/` and triggers a reload, killing the in-flight analysis.

### Solution

Set `CLONED_REPOS_PATH` to a path **outside** the project tree:

```env
# Windows
CLONED_REPOS_PATH=C:/repo_intelligence_storage/cloned_repos

# macOS / Linux
CLONED_REPOS_PATH=/var/lib/repo_intelligence/cloned_repos
```

Alternatively, leave it blank to use the default `~/.repo_intelligence/cloned_repos`.

---

## SSE Stream Terminates Prematurely

### Symptom

The frontend shows a connection error mid-analysis. The backend log stops at a phase like `building_symbols` or `generating_embeddings`.

### Root Cause

1. **Port mismatch**: Multiple backend processes running on different ports
2. **Reverse proxy buffering**: Nginx or Cloudflare buffers the event stream

### Solution

Stop all Python/Uvicorn processes:

**Windows:**
```powershell
Get-Process -Name python, uvicorn -ErrorAction SilentlyContinue | Stop-Process -Force
```

**macOS / Linux:**
```bash
pkill -f uvicorn; pkill -f "python backend"
```

Restart on port 8001:
```bash
python backend/main.py
```

For reverse proxy buffering, add these Nginx settings:
```nginx
proxy_set_header Connection '';
proxy_http_version 1.1;
chunked_transfer_encoding off;
proxy_buffering off;
proxy_cache off;
```

---

## NVIDIA NIM Rate Limit (HTTP 429)

### Symptom

Issue Mapper or chat responses return generic, keyword-based plans without rich LLM-generated steps. The backend log shows:
```
HTTPStatusError: Client error '429 Too Many Requests'
```

### Root Cause

NVIDIA NIM free-tier keys are rate-limited to approximately 3 requests per minute.

### Solution

The system has an automated fallback mode. When a rate limit is detected:
1. The `ProviderManager` circuit breaker opens for the rate-limited provider
2. Requests are routed to the secondary provider (if configured and healthy)
3. If no provider is available, the `FallbackRenderer` generates a structured retrieval-grounded response from ChromaDB chunks without calling any LLM

To permanently resolve, upgrade to a paid NVIDIA NIM tier or switch to Gemini (`LLM_PROVIDER=gemini`).

---

## Chat Always Returns Fallback Responses

### Symptom

Chat responses consistently come from the FallbackRenderer (the response includes "AI is temporarily unavailable" messaging) even though the server started successfully.

### Solution

1. Check provider health: `GET /api/chat/health`
2. Look at `authenticated` and `error_type` fields in the response
3. If `error_type` is set, follow the guidance in the `recommendation` field
4. After fixing `.env`, call `POST /api/chat/reload` to reload providers without restarting
5. Re-check: `GET /api/chat/health` should return `"status": "ok"`

---

## Analysis Store Not Loading on Startup

### Symptom

Previously analyzed repositories are not available after a server restart. `GET /api/repos/recent` returns an empty list.

### Root Cause

The `data/analysis_store.json` file does not exist or is malformed.

### Solution

If the file exists but is malformed, the startup log will show:
```
WARNING: Could not read analysis store from disk: ...
```

Delete the corrupted file:
```bash
rm data/analysis_store.json
```

Then re-analyze the repositories you need. Alternatively, restore from a backup.

---

## POST /api/repos/repair

If a repository shows in `GET /api/repos/recent` but graph or symbol operations return 404, the indexes may be missing or stale:

```bash
curl -X POST http://localhost:8001/api/repos/repair \
  -H "Content-Type: application/json" \
  -d '{"owner": "fastapi", "repo": "fastapi"}'
```

This rebuilds the dependency graph and symbol index from the already-cloned repository on disk without re-cloning or re-embedding.

---

## High Indexing Times for Large Repositories

### Symptom

Analyzing a repository with > 1 000 files takes 10+ minutes.

### Root Cause

BGE embedding generation runs on CPU via SentenceTransformers. Batch embedding on CPU is slow for large chunk counts.

### Solution

- Use incremental analysis after the initial full build — `POST /api/analyze` with `force_rebuild: false` (default) only re-processes changed files
- Ensure `CLONED_REPOS_PATH` is on an SSD
- On GPU-equipped machines, SentenceTransformers will automatically use CUDA if available

---

## PR Analysis Returns 404

### Symptom

`POST /api/pr/analyze` returns 404.

### Root Cause

The repository has not been analyzed yet, or the graph/symbol indexes are missing.

### Solution

1. Check `GET /api/pr/health?owner=owner&repo=repo` for diagnostic details
2. If `analysis_exists: false`, run `POST /api/analyze` first
3. If `graph_available: false` or `symbol_index_available: false`, run `POST /api/repos/repair`
