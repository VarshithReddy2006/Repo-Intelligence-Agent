# Production Status — v1.0.0

This document tracks feature coverage, validation results, known limitations, and technical debt for Repo Intelligence Agent v1.0.

---

## Feature Completeness: 100% (v1.0 Release)

All core analysis, semantic retrieval, SSE streaming, multi-provider LLM reasoning, AST parsing, repository chat, call graph intelligence, API surface analysis, git history mining, PR risk assessment, architecture drift, dead code detection, and the repository intelligence report are fully implemented and verified.

**535 tests passing.**

---

## Implemented Features

### Core Pipeline
1. **Repository Analysis (`POST /api/analyze`)** — Git clone, tech stack detection, code chunking (1500 chars / 200 overlap), local BGE embedding, ChromaDB indexing, NetworkX graph, architecture summary. Supports incremental rebuilds — only changed files re-processed using SHA-256 file hash manifests.

2. **Semantic Retrieval (`POST /api/retrieve`)** — Dense vector search with BGE embeddings and ChromaDB metadata filters.

3. **Repository Chat (`POST /api/chat`)** — v2 pipeline: rule-based intent detection (9 types, zero LLM calls), intent routing to structured services, tier-weighted retrieval (top-15 reranked to top-5), token-budgeted context assembly, multi-provider streaming with circuit breaker failover, conversation memory with pronoun resolution, professional fallback renderer.

4. **Issue Mapper (`POST /api/issues/map`)** — Exactly 2 LLM calls: parse + rank files, then generate grounded implementation plan. Caches by `sha256(issue_text)`.

5. **Architecture Builder (`POST /api/architecture/build`)** — Tree-sitter AST extraction (Python, JS, TS, JSX, TSX) + NetworkX DiGraph. React Flow visualization via `/api/architecture/{owner}/{repo}/graph`.

6. **Reading Order (`POST /api/reading-order`)** — Centrality-based file ranking with entry-point boost, degree centrality, core package boost, peripheral penalties.

7. **Impact Analysis (`POST /api/impact-analysis`)** — BFS forward/reverse traversal up to depth 4, risk scoring.

### Intelligence Features
8. **Interactive Dependency Graph (`/api/graph/`)** — Full graph, neighborhood inspection, forward/backward BFS traces, node search.

9. **Symbol Intelligence (`/api/symbols/`)** — AST symbol index (classes, functions, methods), definition lookup, cross-file references.

10. **Call Graph Intelligence (`/api/call-graph/`)** — Function-level call graph, callers, callees, hierarchy walks, blast-radius, BFS traces.

11. **API Surface Intelligence (`/api/api-surface/`)** — Public/internal/deprecated symbol classification, Martin's instability metrics, breaking change detection.

12. **Git History & Churn (`/api/churn/`)** — Per-file churn scores, hotspot detection (churn × centrality), weekly timeline.

13. **PR Intelligence (`/api/pr/analyze`)** — Size classification (XS–XL), blast radius (LOW–EXTREME) with depth promotion, symbol diffs, focused review areas.

14. **Architecture Drift (`/api/architecture/drift`)** — Virtual delta-patch of dependency graph, added/removed edges, cycle changes, coupling shifts.

15. **Dead Code Detection (`/api/dead-code/analyze`)** — Reachability sweep from entry points, unused files, orphan modules, dead dependency chains, weighted cleanup score (0–100).

16. **Repository Intelligence Report (`/api/v1/report/`)** — Unified health report with 5-dimension scoring, HTML/PDF/Markdown export, SQLite persistence.

### Infrastructure
17. **Authentication Hardening** — Startup provider validation with error classification, fail-fast in production, `GET /api/chat/health` live diagnostic, `POST /api/chat/reload` hot-reload.

18. **Incremental Build System** — Change detector, build manifests, schema versioning, partial symbol/graph/call graph rebuilds.

19. **Prometheus Metrics (`GET /metrics`)** — HTTP counters, active requests gauge, build durations, task durations, cache hit/miss.

20. **Structured Logging** — `CHAT_PIPELINE` log per request, `LLM_PROVIDER_HEALTH` at startup, JSON format available.

---

## Known Limitations

- **No user authentication**: The API is publicly accessible. Use a reverse proxy with auth for multi-tenant deployments.
- **CPU embedding bottleneck**: BGE runs on CPU. Indexing large repositories (> 1 500 chunks) takes 2–3 minutes.
- **Single-instance only**: SQLite and local ChromaDB are not suitable for multi-instance horizontal scaling.
- **`stability.py` router**: Registered but contains no endpoints. Module stability data is accessible via `RepositoryContext.module_stability`.
- **`dependency_smells.py` router**: Registered but contains no endpoints.

---

## Technical Debt (Skeletal Stubs)

| Module | Status | Current Handling |
|---|---|---|
| `agents/analyzer.py` — `RepositoryAnalyzer` | Stub — `NotImplementedError` | Ingestion inlined in `backend/routers/repositories.py` |
| `agents/explainer.py` — `ArchitectureExplainer` | Stub — `NotImplementedError` | Reading order in `services/reading_order_service.py` |
| `memory/sqlite_store.py` — `SQLiteStore` | Stub — `NotImplementedError` | Analysis stored in JSON files; reports use SQLite directly |
| `services/mcp_service.py` — `MCPService` | Stub — `NotImplementedError` | MCP exposed via `backend/mcp_server.py` and `backend/cli.py` |

---

## Roadmap (Post v1.0)

### v1.1 (Near-term)
- [ ] Implement Module Stability endpoints (`backend/routers/stability.py`)
- [ ] Implement Dependency Smells endpoints (`backend/routers/dependency_smells.py`)
- [ ] Restrict CORS origins validation in production configuration guide
- [ ] Enhance SSE error message UX for LLM fallback scenarios

### v2.0 (Long-term)
- [ ] Migrate SQLite to PostgreSQL for multi-instance support
- [ ] Distributed ChromaDB or alternative vector database
- [ ] Redis for distributed caching
- [ ] Authentication/authorization layer
- [ ] GitHub App integration for automated PR risk assessment
- [ ] VS Code Extension
