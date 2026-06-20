# MVP Release Notes (v1.0.0-mvp)

We are proud to announce the initial release of the **Repo Intelligence Agent** MVP. This release delivers a fully functional AI-powered platform for codebase parsing, semantic retrieval, conversational chat, architecture mapping, and issue localization.

---

## 🚀 Key Features Added (v1.0.0-mvp)

- **Unified Repository Workspace:** Dashboard layout integrating Codebase Analysis, Architecture Graph, Reading Path, Impact Analysis, Issue Intelligence, and Chat in a single session.
- **Session Persistence:** Synchronizes active repository context using browser `localStorage` and hydrates repository ingestion lists from `data/analysis_store.json` at startup.
- **Chat Fallback Mode:** Implements an automated local RAG fallback layer that intercepts LLM timeouts, network failures, or HTTP 429 quota exhaustion on NVIDIA NIM, providing cited local context without throwing errors.
- **Architecture Graph:** Uses Tree-sitter and NetworkX to parse syntax imports and export a React Flow-compatible JSON layout.
- **Reading Order:** Generates a structured developer onboarding sequence by ranking files topologically using NetworkX normalized centrality models.
- **Impact Analysis:** Walks forward/reverse dependency paths (depth = 4) and performs component matching to assess code modification risk levels.
- **Issue Mapper:** Automatically maps GitHub issue text to files and compiles step-by-step plans under a budget of exactly two LLM completions.

---

## 🛠️ Issues & Bug Fixes Resolved (v1.0.0-mvp)

- **Current Workspace session bug:** Resolved page reload/navigation resets by storing active context in `localStorage` and sharing it via parent workspace state, eliminating the need to re-analyze when switching tabs.
- **Architecture graph generation:** Patched the AST parsing engine to output empty checks cleanly, enabling the UI to render React Flow graphs or 404 warnings without locking up.
- **Graph persistence:** Standardized atomic writes to `data/architecture/` and `data/analysis_store.json` on successful analysis.
- **Stale issue cache:** Migrated the caching key to `f"{repo_name}:v2:{issue_hash}"`, preventing cross-repository plan bleeding.
- **Chroma dimension mismatch:** Aligned collection indexes to a static 384-dimensional schema matching local `BAAI/bge-small-en-v1.5` embeddings.
- **NVIDIA NIM model configuration:** Corrected parameters to map OpenAI-compatible calls to `deepseek-ai/deepseek-v4-flash` via `https://integrate.api.nvidia.com/v1`.
- **WatchFiles reload issue:** Configured `uvicorn` in `backend/main.py` to monitor source directories specifically (`_RELOAD_DIRS = ["backend", "services", "agents", "memory", "models"]`). This stops Uvicorn from scanning `data/` or cloning directories, preventing reload loops that terminate active requests.
- **API Port Parity:** Configured the application to default consistently to port **8001** for development environments, resolving mismatches between testing tools and gateway servers.

---
---

# Phase 2 Release Notes (v2.0.0-hardened)

We are thrilled to release **Phase 2** of the **Repo Intelligence Agent**, delivering deep codebase analysis, interactive graph manipulation, change tracking, and dead code identification. This release hardened the authentication layer, resolved rate-limiting diagnostics, and passed extensive end-to-end (E2E) verification on real-world Git pull requests.

---

## 🚀 Key Features Added (v2.0.0)

### 1. Interactive Dependency Graph (PH2-001)
- **Granular Navigation:** Supports zooming, dragging, and full text search highlighting.
- **Single-Node Focus:** Endpoint (`GET /api/graph/{owner}/{repo}/neighbors/{node}`) filters view to immediate import neighbors (predecessors and successors) for high-density folders.
- **BFS Reachability Tracing:** Trace forward dependencies (imported files), backward dependents (files importing the target), or both, limited by BFS depth to analyze change propagation.

### 2. AST Symbol Intelligence (PH2-002)
- **Symbol Extraction:** Generates cross-referenced symbol tables (classes, functions, methods) defined inside Python, JS, and TS files.
- **Definition & Reference Lookups:** Find declaration files, class memberships, and lines of code of any given symbol. Find name-based cross-file references instantly.

### 3. Pull Request (PR) Intelligence (PH2-003)
- **Change Risk Assessment:** Analyzes pull request changes to classify PR size (`XS` to `XL`) and blast radius propagation (`LOW` to `EXTREME`) with propagation depth promotions.
- **Symbol Diffs:** Maps modified file paths to affected functions and classes, showing symbol additions, modifications, and deletions.

### 4. Architecture Drift Detection (PH2-004)
- **Graph Delta Patching:** Virtualizes the codebase structure after applying the PR changes ($G_{\text{after}}$) by fetching and parsing updated source file contents from the HEAD branch.
- **Drift Metrics:** Identifies added/removed dependency paths, new cyclic import dependencies, coupling shifts (degree changes), and architectural hotspot modifications.

### 5. Dead Code Intelligence (PH2-005)
- **Reachability Sweep:** Computes topological reachability from entry points (e.g., `main.py`, `app.js`, `api.py`) to discover unused/orphaned modules.
- **Graph-Weighted Cleanup Score:** Deducts points based on degree centrality, out-degree, and cascading subtree sizes to rate repository cleanliness.
- **Dead Dependency Chains:** Traces weakly connected unreachable modules to locate files that can be safely deleted together.

### 6. Centralized Authentication & Hardening
- **Centralized Config:** Hardened PAT handling using `GitHubConfig` to resolve connection discrepancies.
- **Observability Diagnostics:** Added 5-stage logging in `services/pr_intelligence_service.py` to trace payload parsing, symbol index loading, BFS walks, and risk classifications.
- **Rate Limit Telemetry:** Updated `/api/pr/health` to expose rate limit remainders, auth tier status, and local indexes availability.

---

## 🧪 E2E Verification Pass

We verified the PR Intelligence enrichment pipeline across two contrasting test scenarios:
1. **Empty Change PR (PR #1):** Verified that PR #1, which contains zero code changes, correctly evaluates to `0 changed files`, `0 matched symbols`, `LOW` blast radius, and `XS` PR size.
2. **Populated Change PR (PR #2):** Verified that PR #2, which contains extensive changes, executes end-to-end returning HTTP 200:
   - **Changed Files:** 24 files mapped.
   - **AST Symbols Matched:** 77 symbols.
   - **Impact Radius:** 11 downstream affected files.
   - **Propagation Depth:** 3 levels, correctly triggering depth promotion heuristics.
   - **Drift & Hotspots:** Resolved cyclic dependencies, coupling metrics, and mapped entry point changes cleanly.
