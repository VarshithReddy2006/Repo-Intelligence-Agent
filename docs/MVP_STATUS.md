# MVP Status & Release Readiness

This document tracks the feature coverage, validation results, known limitations, technical debt, and future roadmap of the **Repo Intelligence Agent** MVP and Phase 2 releases.

---

## 📊 Feature Completeness: 100% (Phase 2 Hardened)

All core codebase analysis, semantic retrieval, real-time SSE streaming, multi-language AST parsing, reading order centrality, BFS impact analysis, unified workspace navigation, interactive graph operations, symbol intelligence, PR risk profiling, architectural drift, and dead code reachability calculations are fully functional, hardened, and verified.

---

## ✅ Completed Features

The following features and pipelines are implemented and verified:

1. **Repository Ingestion & Analysis (`/api/analyze`)**
   - Direct Git cloning, language detection, codebase chunking (1500 chars / 200 overlap), local BGE embedding, ChromaDB vector indexing, NetworkX graph assembly, DeepSeek architecture summary, and filesystem persistence to `data/analysis_store.json`.
2. **Semantic Retrieval (`/api/retrieve`)**
   - Dense vector matching using local BGE embeddings and ChromaDB metadata filters.
3. **Conversational Chat (`/api/chat`)**
   - Real-time token streaming (SSE) with chat history, architecture context prompt injection, EvaluationAgent validation, and automated local fallback mode.
4. **Issue Mapper (`/api/issues/map`)**
   - Maps issue descriptions to code targets and generates plans under a budget of exactly two LLM calls, utilizing local caching via `f"{repo_name}:v2:{issue_hash}"` and keyword-based fallback steps.
5. **Architecture Builder & Visualizer (`/api/architecture/.../graph`)**
   - Tree-sitter structural extraction (imports, exports, classes, methods, functions) combined with NetworkX DiGraphs to export React Flow visual data.
6. **Reading Path Timeline (`/api/reading-order`)**
   - Centrality-based ranking (entry boost, degree centrality, core boosts, peripheral penalties) combined with topological sorts.
7. **Impact Analysis (`/api/impact-analysis`)**
   - Traverses forward and reverse import paths (BFS up to depth 4) to predict risk levels.
8. **Unified Workspace Navigation**
   - React state caches fetched analysis metadata, allowing instant tab switching on the frontend dashboard without re-analysis.
9. **Session Persistence Store**
   - Syncs active repository parameters via browser `localStorage` and hydrates backend analysis logs from disk upon startup.
10. **Chat Fallback Mode**
    - Intercepts NIM rate-limit (HTTP 429) or provider failures to generate a retrieval-grounded fallback response directly to the user.
11. **Interactive Dependency Graph (`/api/graph/...`) [NEW]**
    - Zoom/drag/pan navigation, neighborhood filter walks (focus file + predecessors + successors), and forward/backward BFS reachability traces.
12. **AST Symbol Intelligence (`/api/symbols/...`) [NEW]**
    - AST symbol declarations index (classes, functions, methods) with direct definition jumping and cross-file references lookups.
13. **PR Intelligence & Risk Assessment (`/api/pr/...`) [NEW]**
    - Pull request analysis computing size categories (XS-XL) and blast radius risk (LOW-EXTREME) with depth-promotion logic, alongside modified symbol highlights.
14. **Architecture Drift Detection (`/api/architecture/drift`) [NEW]**
    - Virtualizes graph states ($G_{\text{after}}$) via delta patching. Reports added/removed edges, coupling increases/decreases, cycle modifications, and hotspot changes.
15. **Dead Code Intelligence (`/api/dead-code/analyze`) [NEW]**
    - Sweep reachability from entry points to discover unused code, orphaned modules, and dead dependency chains using a graph-weighted cleanup score.

---

## 🔧 Known Limitations

- **Local CPU Embedding Bottleneck:** Embedding generation runs locally on CPU using SentenceTransformers. Indexing a large repository can take 2–3 minutes per 1,500 chunks.
- **NVIDIA NIM Free-Tier Quota:** Free developer keys are capped at ~3 requests/minute. The system handles this with its automated fallback mode.
- **No API Authentication:** Backend API routes currently do not verify user identity.
- **Cache Invalidation:** Modifying local files does not auto-update the vector space or import graph. Re-indexing is required.

---

## ⚠️ Technical Debt & Skeletal Stubs

The following components are architectural design stubs that raise `NotImplementedError`. Their functions are currently inlined within API routes or handled via JSON flat files:

- **`SQLiteStore` (`memory/sqlite_store.py`):** Stub for transactional database logs.
- **`MCPService` (`services/mcp_service.py`):** Stub for Model Context Protocol.
- **`RepositoryAnalyzer` (`agents/analyzer.py`):** Stub for agent-based ingestion walks.
- **`ArchitectureExplainer` (`agents/explainer.py`):** Stub for agent-based centrality explanation.

---

## 🗺️ Roadmap

### Phase 1: Stability & Security (Near-term)
- [ ] Connect `SQLiteStore` to record query history and workspace settings.
- [ ] Implement JWT token authentication middleware.
- [ ] Optimize BGE document embedding by omitting query search prefixes on chunking.

### Phase 2: Complete Features (Completed)
- [x] Zoomable/searchable interactive dependency graph.
- [x] Neighborhood file and dependency reachability traces.
- [x] AST symbol indexing and referencing.
- [x] PR size and blast radius risk categorization.
- [x] Architecture drift, coupling, and cycle updates.
- [x] Dead code, orphan module, and dependency chains sweep.

### Phase 3: Continuous Integration (Medium-term)
- [ ] GitHub App integration for automated PR risk assessment and impact reporting.
- [ ] VS Code Extension.
