# Troubleshooting Guide

This document maps common runtime issues, configuration pitfalls, and errors experienced during the development and testing of the **Repo Intelligence Agent** platform, alongside step-by-step resolution procedures.

---

## 📥 HuggingFace Model Download Failures

### Symptom
On the first startup of the backend server, the process appears to hang or throws a `RequestError` during the download of `BAAI/bge-small-en-v1.5`.

### Root Cause
The `SentenceTransformer` package downloads the embedding model (~130 MB) automatically from the HuggingFace Hub on initial execution. Network restrictions, corporate firewalls, or HuggingFace rate-limiting can interrupt this download.

### Solution
1. **Pre-download the model manually** using Python in a terminal with your active virtual environment:
   ```bash
   python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"
   ```
2. **Configure an access token** if encountering rate-limiting:
   - On Windows (PowerShell):
     ```powershell
     $env:HF_TOKEN="your_huggingface_token_here"
     ```
   - On macOS / Linux:
     ```bash
     export HF_TOKEN="your_huggingface_token_here"
     ```

---

## ⚡ High Indexing Times for Large Codebases

### Symptom
Analyzing a repository with more than 1,000 files takes longer than 15–20 minutes, while CPU usage spikes to 100%.

### Root Cause
Embedding generation runs locally. On CPU architectures without acceleration, batch computing is slow.

### Solution
1. Verify the configuration matches the lightweight BGE model in your `.env` (avoid using larger variants like `bge-large-en` unless running on a GPU-enabled machine).
2. Start the FastAPI backend with multi-worker threads or increase the batch size inside `services/embedding_service.py` once GPU resources are available.

---

## 📐 ChromaDB Dimension Mismatch

### Symptom
Calling `/api/index` or `/api/analyze` raises:
`ValueError: Collection dimension mismatch...` or `IndexError: dimension of input vector does not match`.

### Root Cause
This occurs if the embedding provider or model was changed (e.g., from Gemini's 768-dimensional embeddings to BGE's 384-dimensional embeddings) while retaining the old vector store directory.

### Solution
You must reset the Chroma database. This wipes existing cached vectors and prepares the directory for fresh indexing.

**On Windows (PowerShell):**
```powershell
Remove-Item -Recurse -Force data/chroma_db
```

**On macOS / Linux:**
```bash
rm -rf data/chroma_db
```
The database structure will recreate itself automatically on the next analysis request.

---

## 🚫 NVIDIA NIM API Quota Exhaustion (HTTP 429)

### Symptom
Issue Mapper or Q&A requests succeed but return generic, keyword-based plans without rich LLM-generated step-by-step descriptions. The backend log displays `HTTPStatusError: Client error '429 Too Many Requests'`.

### Root Cause
NVIDIA NIM free-tier API keys are rate-limited to approximately ~3 requests per minute. 

### Solution
The system features an **automated grounded fallback mode**. When an LLM rate-limit is detected, the Issue Mapper:
1. Infers affected components using path keyword heuristics (e.g. matching `auth` for authentication, `route` for API layer).
2. Generates implementation steps using raw text snippets extracted from the top-k retrieved codebase chunks.
To resolve this permanently, upgrade to a paid NVIDIA NIM tier or configure key rotation in your env.

---

## 🔄 Server-Sent Events (SSE) Stream Terminated Prematurely

### Symptom
The UI displays a connection error during analysis, and the terminal log halts at `START: chroma indexing`.

### Root Cause
1. **Parallel Port Mismatch:** You might be running multiple backend processes. If `test_analyze.py` is targeting port `8001` while the active server is listening on port `8000`, or vice-versa, commands will hit a mismatched session state. The default server port configured in `backend/main.py` is **8001**.
2. **Reverse Proxy Buffering:** If deploying behind Nginx or Cloudflare, the proxy might buffer the event stream, causing a timeout or socket termination.

### Solution
- Stop all Python/Uvicorn processes:
  - On Windows:
     ```powershell
     Get-Process -Name python, uvicorn -ErrorAction SilentlyContinue | Stop-Process -Force
     ```
  - On macOS/Linux:
     ```bash
     killall python uvicorn
     ```
- Re-run Uvicorn on port **8001**:
  ```bash
  python backend/main.py
  ```
- Ensure reverse proxy settings disable buffering:
  ```nginx
  proxy_set_header Connection '';
  proxy_http_version 1.1;
  chunked_transfer_encoding off;
  proxy_buffering off;
  proxy_cache off;
  ```
