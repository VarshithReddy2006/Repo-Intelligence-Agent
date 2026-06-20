# MVP Release Notes (v1.0.0-mvp)

We are proud to announce the initial release of the **Repo Intelligence Agent** MVP. This release delivers a fully functional AI-powered platform for codebase parsing, semantic retrieval, conversational chat, architecture mapping, and issue localization.

---

## 🚀 Key Features Added

- **Unified Repository Workspace:** Dashboard layout integrating Codebase Analysis, Architecture Graph, Reading Path, Impact Analysis, Issue Intelligence, and Chat in a single session.
- **Session Persistence:** Synchronizes active repository context using browser `localStorage` and hydrates repository ingestion lists from `data/analysis_store.json` at startup.
- **Chat Fallback Mode:** Implements an automated local RAG fallback layer that intercepts LLM timeouts, network failures, or HTTP 429 quota exhaustion on NVIDIA NIM, providing cited local context without throwing errors.
- **Architecture Graph:** Uses Tree-sitter and NetworkX to parse syntax imports and export a React Flow-compatible JSON layout.
- **Reading Order:** Generates a structured developer onboarding sequence by ranking files topologically using NetworkX normalized centrality models.
- **Impact Analysis:** Walks forward/reverse dependency paths (depth = 4) and performs component matching to assess code modification risk levels.
- **Issue Mapper:** Automatically maps GitHub issue text to files and compiles step-by-step plans under a budget of exactly two LLM completions.

---

## 🛠️ Issues & Bug Fixes Resolved

- **Current Workspace session bug:** Resolved page reload/navigation resets by storing active context in `localStorage` and sharing it via parent workspace state, eliminating the need to re-analyze when switching tabs.
- **Architecture graph generation:** Patched the AST parsing engine to output empty checks cleanly, enabling the UI to render React Flow graphs or 404 warnings without locking up.
- **Graph persistence:** Standardized atomic writes to `data/architecture/` and `data/analysis_store.json` on successful analysis.
- **Stale issue cache:** Migrated the caching key to `f"{repo_name}:v2:{issue_hash}"`, preventing cross-repository plan bleeding.
- **Chroma dimension mismatch:** Aligned collection indexes to a static 384-dimensional schema matching local `BAAI/bge-small-en-v1.5` embeddings.
- **NVIDIA NIM model configuration:** Corrected parameters to map OpenAI-compatible calls to `deepseek-ai/deepseek-v4-flash` via `https://integrate.api.nvidia.com/v1`.
- **WatchFiles reload issue:** Configured `uvicorn` in `backend/main.py` to monitor source directories specifically (`_RELOAD_DIRS = ["backend", "services", "agents", "memory", "models"]`). This stops Uvicorn from scanning `data/` or cloning directories, preventing reload loops that terminate active requests.
- **API Port Parity:** Configured the application to default consistently to port **8001** for development environments, resolving mismatches between testing tools and gateway servers.
