# MVP Status & Release Readiness

This document tracks the feature coverage, validation results, known limitations, technical debt, and future roadmap of the **Repo Intelligence Agent** MVP release.

---

## 📊 MVP Completeness: 97%

The core codebase analysis, semantic retrieval, SSE streaming, and issue mapping pipelines are fully functional and tested. The remaining 3% corresponds to skeletal agents and minor performance improvements.

---

## ✅ Completed Features

The following key services and pipelines are implemented and verified:

1. **Repository Analysis Pipeline (`/api/analyze`)**
   - Streamed cloning, extraction, tech stack detection, chunking (1500 chars / 200 overlap), local BGE embedding, ChromaDB indexing, and LLM-driven architecture summary.
2. **Semantic Retrieval (`/api/retrieve`)**
   - Local embedding + cosine similarity search over repository chunks, backed by LLM answers.
3. **Repository Chat (`/api/chat`)**
   - Multi-turn conversational Q&A over codebase with SSE streaming and source citations.
4. **Issue Mapper (`/api/issues/map`)**
   - Grounded file mapping and implementation plan generation.
5. **Architecture Builder (`/api/architecture/build`)**
   - Dependency graph generation using Tree-sitter AST parsing and NetworkX centrality scoring.
6. **Visualization Endpoint (`/api/architecture/.../graph`)**
   - Nodes and edges output compatible with React Flow graphs.
7. **Reading Path & Impact Analysis**
   - Reading order onboarding list and BFS-driven dependent file lists.

---

## 🔧 Known Limitations

- **In-Memory Store:** The `ANALYSIS_STORE` cache (holding active analysis lists) is in-memory and resets when the backend server restarts.
- **Local CPU Embedding Speed:** Running embeddings on large repositories via CPU takes approximately ~2–3 minutes per 1500 chunks.
- **NVIDIA NIM Free-tier Quota:** Free API keys allow a maximum of ~3 requests per minute.
- **Authentication:** Currently, there is no auth middleware or rate-limiting for the backend API endpoints.

---

## ⚠️ Technical Debt & Stubs

The following areas are identified for cleanup or implementation in upcoming minor releases:

- **Skeletal Agents:**
  - `agents/analyzer.py` is a stub that raises `NotImplementedError`. Active analysis logic was inlined into the API.
  - `agents/explainer.py` is a stub that raises `NotImplementedError`. Active explanation logic was inlined into the API.
- **Deferred Evaluator:**
  - `EvaluationAgent` is imported but not fully wired as a gating mechanism (it returns scores but does not block low-confidence responses).
- **Embedding Prefix Optimization:**
  - The local BGE query prefix (`"Represent this sentence for searching relevant passages:"`) is applied to both search queries and chunk documents. While it functions, document embedding should omit the prefix to optimize semantic search recall.

---

## 🗺️ Roadmap

### Phase 1: Stability & Security (Near-term)
- [ ] Implement persistent SQLite backend for `ANALYSIS_STORE`.
- [ ] Add JWT authentication and route-level middleware.
- [ ] Optimize BGE document embedding by omitting the search prefix.

### Phase 2: Hybrid & Multi-Repo (Medium-term)
- [ ] Support hybrid search (BM25 keyword matches + vector search).
- [ ] Enable multi-repository queries.
- [ ] Replace skeletal stubs with active background agent tasks.

### Phase 3: Continuous Integration (Long-term)
- [ ] GitHub App integration for automated PR risk assessment and impact reporting.
- [ ] VS Code Extension.
