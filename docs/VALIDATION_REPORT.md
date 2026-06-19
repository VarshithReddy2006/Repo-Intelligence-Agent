# MVP Validation & Performance Report

This document reports the performance characteristics, indexing metrics, and multi-agent pipeline validation results compiled during the final MVP testing cycle against production-scale repositories.

---

## 📈 Indexing & Storage Metrics

Validation was conducted on the **Ankita15k/GitNest** repository (a full-stack collaborative git hosting system) to evaluate indexing throughput, chunking efficiency, and memory layer density.

| Metric | Measured Value | Notes |
|---|---|---|
| **Total Source Files walked** | 328 files | Skips `node_modules`, `dist`, `.git`, and binaries |
| **Total Chunks generated** | 1,549 chunks | CodeChunker (1500 chars / 200 overlap) |
| **BGE Embedding output** | 1,549 vectors | 384-dimensional local BGE Small embeddings |
| **ChromaDB Write time** | ~28 seconds | Persistent local SSD write speed |
| **Tree-sitter AST parse** | ~1.4 seconds | Python, JavaScript, and TypeScript parsing |
| **Graph Builder edges** | 1,440 dependencies | Dependency edge extraction |
| **Framework Entry Points** | 17 entry points | Filtered via exclusion heuristics |

---

## 🎯 Issue Mapper Validation Results

We tested the **Issue Mapper** using real repository issues. The validation focused on verifying that the mapper retrieves the correct source file context and generates executable steps without hallucinating non-existent paths.

| Tested Issue | Grounded File Targets | Hallucination Detected | Correct Components Identified |
| :--- | :--- | :--- | :--- |
| **"Login fails when password contains @"** | `auth.test.js`, `authStore.js`, `security.test.js` | **None** | `Authentication`, `Frontend`, `Services` |
| **"Pagination broken on repository page"** | `repository.controller.js`, `pullRequest.controller.js`, `App.jsx` | **None** | `API Layer`, `Frontend`, `Services` |
| **"Branch protection approval count incorrect"** | `branchProtectionEvaluator.service.js`, `BranchProtectionRuleCard.jsx` | **None** | `Frontend`, `Services` |

---

## 🔍 API Performance Benchmarks

The following latencies were measured across all backend endpoints:

| Endpoint | Method | Average Latency | Bottleneck |
|---|---|---|---|
| `/health` | GET | `< 3ms` | N/A |
| `/api/repos/examples` | GET | `< 2ms` | N/A |
| `/api/index` | POST | `~ 2.5 minutes` | CPU-bound embedding generation |
| `/api/retrieve` | POST | `~ 150ms` | Network time (NIM API call) |
| `/api/issues/map` | POST | `~ 4.8 seconds` | Sequential LLM calls (Plan + Steps) |
| `/api/architecture/build` | POST | `~ 1.8 seconds` | Tree-sitter file-level parsing |
| `/api/architecture/{owner}/{repo}` | GET | `< 5ms` | Disk read (cached JSON summary) |
| `/api/reading-order` | POST | `~ 80ms` | NetworkX centrality calculations |
| `/api/impact-analysis` | POST | `~ 95ms` | BFS traversal over dependency graph |
