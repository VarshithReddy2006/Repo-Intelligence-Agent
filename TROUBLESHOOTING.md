# Troubleshooting Guide — Repo Intelligence Agent

This guide lists common problems, root causes, and solutions for the Repo Intelligence Agent backend, frontend, and VS Code extension.

---

## 1. LLM & API Key Problems

### Symptom: API Limit Exceeded / Quota Errors (Google Gemini)
- **Error Message**: `ResourceExhausted` or `HTTP 429: Quota exceeded`
- **Cause**: Google AI Studio free tier limits requests to 15 RPM (Requests Per Minute).
- **Solution**:
  1. Configure NVIDIA NIM DeepSeek fallback in `.env` (`LLM_PROVIDER=deepseek`). The system will automatically reroute chat queries when Gemini fails.
  2. Throttle chat queries or wait 60 seconds.
  3. Set a premium Gemini API billing key.

### Symptom: LLM Failover Log Warnings
- **Log Entry**: `Primary LLM provider 'gemini' is unhealthy. ProviderManager will use the fallback provider...`
- **Cause**: Startup validation check failed for Gemini, but DeepSeek is authenticated.
- **Solution**: Check your `GEMINI_API_KEY` spelling and make sure it has not expired. The server will run, but queries will route to DeepSeek.

---

## 2. Ingestion & Database Issues

### Symptom: SQLite Database Locked
- **Error Message**: `sqlite3.OperationalError: database is locked`
- **Cause**: Multiple python processes are writing to `data/repo_understanding.db` concurrently.
- **Solution**:
  1. Close any extra CLI processes or secondary backend instances.
  2. Kill zombie python processes:
     - On Windows: `taskkill /IM python.exe /F`
     - On Linux/macOS: `pkill -f python`

### Symptom: Vector Store (ChromaDB) Write Failures
- **Error Message**: `RuntimeError: chroma_db index not found` or segmentation faults on embedding.
- **Cause**: ChromaDB folder got corrupted during a forced server shutdown.
- **Solution**: Wipe the cache databases and re-analyze the repository:
  ```bash
  rm -rf data/chroma_db data/repo_understanding.db data/cache.json
  ```
  *(Database tables and folders are automatically recreated on server restart)*

---

## 3. Server Startup & Build Errors

### Symptom: Uvicorn Reload Loop
- **Symptom**: Backend restarts constantly when analyzing a repository.
- **Cause**: Uvicorn is watching the entire directory tree. When a repository is cloned to `data/cloned_repos/`, the file writes trigger uvicorn to restart, killing active parsing tasks.
- **Solution**: Exclude the data path using the correct directory settings config in `.env`:
  ```env
  CLONED_REPOS_PATH=data/cloned_repos
  ```
  Check `backend/main.py` lines 8-19 to verify that `data/**` is included in `_RELOAD_EXCLUDES`.

### Symptom: Astro Dev Server Port Conflict
- **Error Message**: `Port 4321 is already in use`
- **Cause**: Another development server is running.
- **Solution**:
  - Run Astro on a different port: `npm run dev -- --port 4322`
  - Update `FRONTEND_URL=http://localhost:4322` in your `.env` so CORS middleware is mapped correctly.

---

## 4. VS Code Extension Debugging

### Symptom: CodeLens or Hovers Do Not Show Up
- **Cause**: The extension cannot reach the backend server, or the active repository is not set.
- **Solution**:
  1. Verify the backend server is running on `http://127.0.0.1:8001`.
  2. Open VS Code Settings, search for `repoIntelligence.backendUrl`, and verify it matches the backend address.
  3. Run the Command Palette command: `Repo Intelligence: Set Active Repository` and type in the `owner/repo` identifier (e.g. `fastapi/fastapi`).
