# API Reference Specification

All endpoints are hosted at: `http://127.0.0.1:8001`

---

## 🧭 Navigation

- [System Status & Utility](#system-status--utility)
- [Repository Processing](#repository-processing)
- [Semantic Querying](#semantic-querying)
- [Architecture Intelligence](#architecture-intelligence)
- [Interactive Graph Intelligence (Phase 2)](#interactive-graph-intelligence-phase-2)
- [Symbol Intelligence (Phase 2)](#symbol-intelligence-phase-2)
- [PR & Architecture Drift Intelligence (Phase 2)](#pr--architecture-drift-intelligence-phase-2)
- [Dead Code Intelligence (Phase 2)](#dead-code-intelligence-phase-2)

---

## System Status & Utility

### GET /health
Retrieve the operational status of the API services and configured LLM providers.

#### Request Example
```bash
curl http://127.0.0.1:8001/health
```

#### Response (200 OK)
```json
{
  "backend": "online",
  "llm_provider": "deepseek",
  "llm_model": "deepseek-ai/deepseek-v4-flash",
  "embedding_provider": "bge-small-en-v1.5",
  "vector_db": "chromadb",
  "status": "healthy"
}
```

---

### GET /api/repos/examples
Fetch a list of pre-configured example repositories designed for testing.

#### Request Example
```bash
curl http://127.0.0.1:8001/api/repos/examples
```

#### Response (200 OK)
```json
[
  {
    "name": "google/guava",
    "url": "https://github.com/google/guava",
    "tech_stack": ["Java", "Maven"],
    "description": "Google core libraries for Java."
  },
  {
    "name": "fastapi/fastapi",
    "url": "https://github.com/fastapi/fastapi",
    "tech_stack": ["Python", "Pydantic", "Starlette"],
    "description": "High performance, easy to learn, fast to code, ready for production API framework."
  },
  {
    "name": "vercel/next.js",
    "url": "https://github.com/vercel/next.js",
    "tech_stack": ["JavaScript", "TypeScript", "React", "Rust"],
    "description": "The React Framework for the Web."
  }
]
```

---

### GET /api/repos/recent
Fetch a list of repositories processed during the current server session, loaded from the persisted store.

#### Request Example
```bash
curl http://127.0.0.1:8001/api/repos/recent
```

#### Response (200 OK)
```json
[
  {
    "name": "Ankita15k/GitNest",
    "url": "https://github.com/Ankita15k/GitNest",
    "tech_stack": ["JavaScript", "TypeScript"],
    "analyzed_at": "Just now"
  }
]
```

---

## Repository Processing

### POST /api/analyze (SSE Stream)
Trigger a full repository cloning, language parsing, code chunking, indexing, and architecture mapping pipeline. This endpoint streams real-time progress events using the `text/event-stream` mime-type.

#### Request Schema (AnalyzeRequest)
- `url` (string, required): GitHub repository URL.
- `branch` (string, optional): Git branch or ref. Defaults to `"main"`.
- `model` (string, optional): LLM model variant to use. Defaults to `"deepseek-ai/deepseek-v4-flash"`.

```json
{
  "url": "https://github.com/owner/repository",
  "branch": "main",
  "model": "deepseek-ai/deepseek-v4-flash"
}
```

#### Request Example
```bash
curl -N -X POST http://127.0.0.1:8001/api/analyze \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "url": "https://github.com/Ankita15k/GitNest",
    "branch": "main"
  }'
```

#### SSE Stream Events Progress Output
```
data: {"status": "cloning", "message": "Cloning repository from GitHub..."}
data: {"status": "cloned", "message": "✓ Repository cloned successfully"}
data: {"status": "detecting", "message": "Detecting languages and frameworks..."}
data: {"status": "detected", "message": "✓ Technologies detected: ['JavaScript', 'TypeScript']"}
data: {"status": "chunking", "message": "START: chunking"}
data: {"status": "chunking", "message": "END: chunking"}
data: {"status": "embedding", "message": "START: embeddings"}
data: {"status": "embedding", "message": "END: embeddings"}
data: {"status": "chroma", "message": "START: chroma indexing"}
data: {"status": "chroma", "message": "END: chroma indexing"}
data: {"status": "building_graph", "message": "Building file dependency graph..."}
data: {"status": "graph_built", "message": "✓ Dependency graph: 328 files parsed, 1440 edges", "files_parsed": 328, "dependencies_found": 1440, "entry_points": ["backend/src/index.js"]}
data: {"status": "analyzed", "message": "✓ Architecture analyzed"}
data: {"status": "complete", "message": "✓ Repository analysis complete!"}
data: {"status": "done", "repo": "Ankita15k/GitNest"}
```

---

### POST /api/index
Clones, chunks, and indexes a repository's vector embeddings in ChromaDB, without building structural dependency graphs.

#### Request Schema (IndexRequest)
- `repo_url` (string, required): GitHub repository URL.

```json
{
  "repo_url": "https://github.com/owner/repository"
}
```

#### Response (200 OK)
```json
{
  "status": "indexed",
  "files": 328,
  "chunks": 1549
}
```

---

### GET /api/analysis/{owner}/{repo_name}
Fetch the complete metadata results of a repository analysis.

#### Response (200 OK)
```json
{
  "analysis": {
    "structure": {
      ".": ["README.md", "package.json"],
      "src": ["app.js", "server.js"]
    },
    "dependencies": ["express", "cors", "jsonwebtoken"],
    "tech_stack": ["JavaScript", "TypeScript"],
    "metadata": {
      "owner": "Ankita15k",
      "name": "GitNest",
      "local_path": "C:\\Users\\Varshith Reddy\\.repo_intelligence\\cloned_repos\\Ankita15k_GitNest"
    }
  },
  "architecture": {
    "summary": "GitNest is a full-stack Git hosting dashboard built with Node.js and Express...",
    "reading_order": [
      "backend/src/index.js",
      "backend/src/app.js"
    ],
    "relationships": [
      {
        "source": "backend/src/index.js",
        "target": "backend/src/app.js",
        "relationship_type": "imports",
        "description": "Imports app instance to launch listener server."
      }
    ]
  }
}
```

---

## Semantic Querying

### POST /api/retrieve
Query the vector space index directly for a repository using BGE embeddings and generate a grounded LLM response.

#### Request Schema (RetrieveRequest)
- `repo` (string, required): Repository identifier (owner/repo).
- `question` (string, required): Question query.

```json
{
  "repo": "owner/repository",
  "question": "How is authentication handled?"
}
```

#### Response (200 OK)
```json
{
  "answer": "Authentication is implemented using JWT tokens inside authMiddleware.js...",
  "sources": [
    {
      "file": "backend/src/middleware/authMiddleware.js",
      "content": "const token = req.headers.authorization.split(' ')[1]; ...",
      "score": 0.92
    }
  ]
}
```

---

### POST /api/chat (SSE Stream)
Interactive, conversational multi-turn chat over the repository codebase context, streaming back word tokens.

#### Request Schema (ChatRequest)
- `repo` (string, required): Repository identifier (owner/repo).
- `message` (string, required): User message.
- `history` (list, optional): Conversation history turns containing roles and text content.

```json
{
  "repo": "Ankita15k/GitNest",
  "message": "Explain how Socket.io notifies users.",
  "history": [
    {"role": "user", "content": "How are WebSockets set up?"},
    {"role": "assistant", "content": "WebSockets are initialized in socket.js..."}
  ]
}
```

#### Request Example
```bash
curl -N -X POST http://127.0.0.1:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "Ankita15k/GitNest",
    "message": "Explain how Socket.io notifies users.",
    "history": []
  }'
```

#### SSE Stream Output
```
data: {"text": "Socket"}
data: {"text": ".io "}
data: {"text": "notifications "}
data: {"text": "are "}
data: {"text": "pushed "}
data: {"text": "to "}
data: {"text": "clients "}
data: {"text": "using "}
data: {"text": "io.emit()."}
data: {"sources": ["backend/src/socket/notificationHandler.js"], "confidence": 92, "fallback_mode": false, "status": "done"}
```

---

### POST /api/issues/map
Analyze a GitHub issue and map it to relevant source code modules, generating a detailed implementation plan.

#### Request Schema (IssueMapRequest)
- `repo` (string, required): Repository identifier (owner/repo).
- `issue` (string, optional): Combined issue text details.
- `title` (string, optional): GitHub issue title.
- `description` (string, optional): GitHub issue description body.

```json
{
  "repo": "Ankita15k/GitNest",
  "title": "Fix token validation timeout",
  "description": "User tokens expire instantly when hitting the API from mobile clients."
}
```

#### Response (200 OK - IssueMapResponse)
```json
{
  "issue_summary": "Fix token validation timeout",
  "issue_type": "bug",
  "relevant_files": [
    "backend/src/middleware/authMiddleware.js"
  ],
  "affected_components": [
    "Authentication",
    "Services"
  ],
  "implementation_plan": [
    {
      "step_number": 1,
      "description": "Modify the jwt verify expiration range logic inside authMiddleware.js to tolerate mobile clock drift.",
      "files_to_modify": ["backend/src/middleware/authMiddleware.js"]
    }
  ],
  "complexity": "low",
  "confidence": 88,
  "verified": true,
  "sources": [
    "backend/src/middleware/authMiddleware.js"
  ]
}
```

---

## Architecture Intelligence

### POST /api/architecture/build
Trigger Tree-sitter AST parsing over local cloned repository files and construct the dependency NetworkX graph.

#### Request Schema (ArchitectureBuildRequest)
- `repo` (string, required): Repository identifier (owner/repo).

```json
{
  "repo": "owner/repository"
}
```

#### Response (200 OK)
```json
{
  "status": "built",
  "repo": "Ankita15k/GitNest",
  "files_parsed": 328,
  "dependencies_found": 1440,
  "entry_points": [
    "backend/src/index.js"
  ]
}
```

---

### GET /api/architecture/{owner}/{repo_name}
Fetch the generated architecture summary, reading order, and relationship schemas.

#### Response (200 OK - ArchitectureSummary)
```json
{
  "summary": "GitNest is a full-stack Git dashboard using Express and local git hooks...",
  "reading_order": [
    "backend/src/index.js",
    "backend/src/app.js"
  ],
  "relationships": [
    {
      "source": "backend/src/index.js",
      "target": "backend/src/app.js",
      "relationship_type": "imports",
      "description": "Instantiates app config schemas."
    }
  ]
}
```

---

### GET /api/architecture/{owner}/{repo_name}/graph
Retrieve React Flow-compatible node and edge datasets for visualization.

#### Query Parameters
- `q` (string, optional): Substring filter for file names/module paths.

#### Response (200 OK)
```json
{
  "nodes": [
    {
      "id": "backend/src/index.js",
      "data": { "label": "index.js" },
      "position": { "x": 120, "y": 80 },
      "style": { "background": "#1e293b", "color": "#f8fafc" }
    }
  ],
  "edges": [
    {
      "id": "e_backend/src/index.js_backend/src/app.js",
      "source": "backend/src/index.js",
      "target": "backend/src/app.js",
      "animated": true
    }
  ]
}
```

---

### POST /api/reading-order
Generate an optimal, ranked file list for onboarding new developers based on graph centrality metrics.

#### Request Schema (ReadingOrderRequest)
- `repo` (string, required): Repository identifier (owner/repo).

```json
{
  "repo": "owner/repository"
}
```

#### Response (200 OK - ReadingOrder)
```json
{
  "repo": "Ankita15k/GitNest",
  "ordered_files": [
    {
      "rank": 1,
      "file_path": "backend/src/index.js",
      "reason": "Primary application entry point initializing server configurations.",
      "tier": "entry_point",
      "score": 150.0
    }
  ],
  "reasoning": [
    "Timeline starts with detected application entry points.",
    "Order prioritizes modules with high degree centrality scores."
  ],
  "estimated_reading_time": 45,
  "total_files_ranked": 328
}
```

---

### POST /api/impact-analysis
Predict downstream affected modules and components resulting from a proposed change.

#### Request Schema (ImpactAnalysisRequest)
- `repo` (string, required): Repository identifier (owner/repo).
- `issue` (string, required): Change request or GitHub issue text.

```json
{
  "repo": "Ankita15k/GitNest",
  "issue": "Add API key authentication"
}
```

#### Response (200 OK - ImpactAnalysis)
```json
{
  "repo": "Ankita15k/GitNest",
  "issue_text": "Add API key authentication",
  "directly_affected_files": [
    "backend/src/middleware/authMiddleware.js"
  ],
  "indirectly_affected_files": [
    "backend/src/routes/auth.routes.js",
    "backend/src/app.js"
  ],
  "affected_components": [
    "Authentication",
    "API Layer"
  ],
  "risk_level": "medium",
  "estimated_file_count": 3,
  "dependency_paths": [
    {
      "path": [
        "backend/src/middleware/authMiddleware.js",
        "backend/src/routes/auth.routes.js",
        "backend/src/app.js"
      ]
    }
  ],
  "confidence": 85
}
```

---
---

## Interactive Graph Intelligence (Phase 2)

### GET /api/graph/{owner}/{repo}/full
Retrieve the full dependency graph for visualization in the interactive layout.

#### Query Parameters
- `q` (string, optional): Query substring to filter node files.

#### Request Example
```bash
curl http://127.0.0.1:8001/api/graph/VarshithReddy2006/Repo-Intelligence-Agent/full?q=service
```

#### Response (200 OK)
```json
{
  "nodes": [
    {
      "id": "services/symbol_service.py",
      "label": "symbol_service.py",
      "category": "file",
      "language": "python"
    }
  ],
  "edges": [
    {
      "source": "services/symbol_service.py",
      "target": "models/symbol.py",
      "relationship": "imports"
    }
  ]
}
```

---

### GET /api/graph/{owner}/{repo}/neighbors/{node_path:path}
Retrieve the immediate neighborhood of a single file node.

#### Request Example
```bash
curl http://127.0.0.1:8001/api/graph/VarshithReddy2006/Repo-Intelligence-Agent/neighbors/services/symbol_service.py
```

#### Response (200 OK)
```json
{
  "nodes": [
    { "id": "services/symbol_service.py", "label": "symbol_service.py", "category": "focus", "language": "python" },
    { "id": "backend/api.py", "label": "api.py", "category": "predecessor", "language": "python" },
    { "id": "models/symbol.py", "label": "symbol.py", "category": "successor", "language": "python" }
  ],
  "edges": [
    { "source": "backend/api.py", "target": "services/symbol_service.py", "relationship": "imports" },
    { "source": "services/symbol_service.py", "target": "models/symbol.py", "relationship": "imports" }
  ]
}
```

---

### GET /api/graph/{owner}/{repo}/trace/{node_path:path}
Trace all reachable nodes in the dependency graph starting from a node.

#### Query Parameters
- `direction` (string, optional): Direction of walk. Options: `forward`, `backward`, `both`. Defaults to `both`.
- `depth` (int, optional): BFS walk limit. Minimum 1, Maximum 12. Defaults to 6.

#### Request Example
```bash
curl "http://127.0.0.1:8001/api/graph/VarshithReddy2006/Repo-Intelligence-Agent/trace/services/symbol_service.py?direction=backward&depth=3"
```

#### Response (200 OK)
```json
{
  "nodes": [
    { "id": "services/symbol_service.py", "label": "symbol_service.py", "category": "focus", "language": "python" },
    { "id": "backend/api.py", "label": "api.py", "category": "dependent", "language": "python" }
  ],
  "edges": [
    { "source": "backend/api.py", "target": "services/symbol_service.py", "relationship": "imports" }
  ]
}
```

---

### GET /api/graph/{owner}/{repo}/search
Search for nodes by label or file path, returning matches highlighted with their immediate context.

#### Query Parameters
- `q` (string, required): Query term.

#### Request Example
```bash
curl http://127.0.0.1:8001/api/graph/VarshithReddy2006/Repo-Intelligence-Agent/search?q=dead_code
```

#### Response (200 OK)
```json
{
  "nodes": [
    { "id": "services/dead_code_service.py", "label": "dead_code_service.py", "category": "file", "language": "python", "highlighted": true },
    { "id": "backend/api.py", "label": "api.py", "category": "file", "language": "python", "highlighted": false }
  ],
  "edges": [
    { "source": "backend/api.py", "target": "services/dead_code_service.py", "relationship": "imports" }
  ]
}
```

---

## Symbol Intelligence (Phase 2)

### GET /api/symbols/{owner}/{repo}/file/{file_path:path}
Retrieve all AST symbols (classes, functions, methods) defined in a file.

#### Request Example
```bash
curl http://127.0.0.1:8001/api/symbols/VarshithReddy2006/Repo-Intelligence-Agent/file/services/symbol_service.py
```

#### Response (200 OK)
```json
{
  "file": "services/symbol_service.py",
  "repo": "VarshithReddy2006/Repo-Intelligence-Agent",
  "symbol_count": 2,
  "symbols": [
    {
      "name": "SymbolService",
      "type": "class",
      "file_path": "services/symbol_service.py",
      "line_number": 26,
      "language": "python",
      "parent_class": null
    },
    {
      "name": "get_file_symbols",
      "type": "function",
      "file_path": "services/symbol_service.py",
      "line_number": 95,
      "language": "python",
      "parent_class": "SymbolService"
    }
  ]
}
```

---

### GET /api/symbols/{owner}/{repo}/definition/{symbol_name}
Find the definition site of a symbol.

#### Request Example
```bash
curl http://127.0.0.1:8001/api/symbols/VarshithReddy2006/Repo-Intelligence-Agent/definition/SymbolService
```

#### Response (200 OK)
```json
{
  "symbol": "SymbolService",
  "repo": "VarshithReddy2006/Repo-Intelligence-Agent",
  "definition": {
    "name": "SymbolService",
    "type": "class",
    "file_path": "services/symbol_service.py",
    "line_number": 26,
    "language": "python",
    "parent_class": null
  }
}
```

---

### GET /api/symbols/{owner}/{repo}/references/{symbol_name}
Search for references to a symbol across the repository symbol index.

#### Request Example
```bash
curl http://127.0.0.1:8001/api/symbols/VarshithReddy2006/Repo-Intelligence-Agent/references/SymbolService
```

#### Response (200 OK)
```json
{
  "symbol": "SymbolService",
  "repo": "VarshithReddy2006/Repo-Intelligence-Agent",
  "references": [
    {
      "name": "SymbolService",
      "type": "class",
      "file_path": "services/symbol_service.py",
      "line_number": 26,
      "language": "python",
      "parent_class": null
    }
  ],
  "reference_count": 1,
  "note": "MVP: name-based matching only. Full cross-file call graph planned for PH2-003."
}
```

---

## PR & Architecture Drift Intelligence (Phase 2)

### POST /api/pr/analyze
Perform risk assessment, changed files extraction, symbol diffs, and blast radius propagation for a Pull Request.

#### Request Schema (PRAnalyzeRequest)
- `owner` (string, required): GitHub repository owner.
- `repo` (string, required): GitHub repository name.
- `pr_number` (int, required): GitHub pull request ID.

```json
{
  "owner": "VarshithReddy2006",
  "repo": "Repo-Intelligence-Agent",
  "pr_number": 2
}
```

#### Response (200 OK)
```json
{
  "repo": "VarshithReddy2006/Repo-Intelligence-Agent",
  "pr_number": 2,
  "risk_score": 24.5,
  "pr_size": "M",
  "blast_radius": "MEDIUM",
  "changed_files": [
    {
      "filename": "services/pr_intelligence_service.py",
      "status": "modified",
      "additions": 45,
      "deletions": 10,
      "changes": 55
    }
  ],
  "added_symbols": [],
  "modified_symbols": [
    {
      "name": "analyze_pull_request",
      "type": "function",
      "file_path": "services/pr_intelligence_service.py",
      "line_number": 85,
      "language": "python",
      "change_type": "modified",
      "parent_class": "PRIntelligenceService"
    }
  ],
  "removed_symbols": [],
  "affected_files": [
    "backend/api.py"
  ],
  "propagation_paths": [
    {
      "source": "services/pr_intelligence_service.py",
      "target": "backend/api.py",
      "path": ["backend/api.py", "services/pr_intelligence_service.py"],
      "depth": 1
    }
  ],
  "risk_breakdown": {
    "size_risk": "MEDIUM",
    "blast_radius_risk": "LOW",
    "drift_risk": "LOW",
    "hotspot_risk": "HIGH"
  },
  "review_focus_areas": [
    {
      "area": "hotspots",
      "description": "Changes to services/pr_intelligence_service.py modify highly coupled module logic.",
      "severity": "HIGH"
    }
  ],
  "analyzed_at": "2026-06-20T14:14:00Z"
}
```

---

### GET /api/pr/health
Health diagnostics check for PR Intelligence configurations.

#### Query Parameters
- `owner` (string, optional): GitHub owner.
- `repo` (string, optional): GitHub repo.

#### Request Example
```bash
curl "http://127.0.0.1:8001/api/pr/health?owner=VarshithReddy2006&repo=Repo-Intelligence-Agent"
```

#### Response (200 OK)
```json
{
  "github_token": true,
  "github_token_loaded": true,
  "github_token_prefix": "github_pat_1...",
  "github_rate_limit_authenticated": true,
  "rate_limit_remaining": 4982,
  "analysis_exists": true,
  "graph_available": true,
  "symbol_index_available": true,
  "status": "healthy"
}
```

---

### POST /api/repos/repair
Repair a repository by forcefully regenerating its missing graph and symbol indices.

#### Request Schema
- `owner` (string, required): GitHub owner.
- `repo` (string, required): GitHub repo.

```json
{
  "owner": "VarshithReddy2006",
  "repo": "Repo-Intelligence-Agent"
}
```

#### Response (200 OK)
```json
{
  "status": "success",
  "message": "Repository indexes rebuilt successfully for 'VarshithReddy2006/Repo-Intelligence-Agent'",
  "details": {
    "architecture": { "status": "built", "repo": "VarshithReddy2006/Repo-Intelligence-Agent", "files_parsed": 34, "dependencies_found": 80 },
    "symbols": { "repo": "VarshithReddy2006/Repo-Intelligence-Agent", "symbols_parsed": 122 }
  }
}
```

---

### POST /api/architecture/drift
Detect architectural drift, cycle additions, and coupling shifts introduced by a Pull Request.

#### Request Schema (PRDriftRequest)
- `owner` (string, required): GitHub owner.
- `repo` (string, required): GitHub repo.
- `pr_number` (int, required): GitHub PR ID.

```json
{
  "owner": "VarshithReddy2006",
  "repo": "Repo-Intelligence-Agent",
  "pr_number": 2
}
```

#### Response (200 OK)
```json
{
  "repo": "VarshithReddy2006/Repo-Intelligence-Agent",
  "pr_number": 2,
  "added_dependencies": [],
  "removed_dependencies": [],
  "new_cycles": [],
  "resolved_cycles": [],
  "coupling_increase": [
    { "file": "services/pr_intelligence_service.py", "before": 4, "after": 5 }
  ],
  "coupling_decrease": [],
  "new_entry_points": [],
  "removed_entry_points": [],
  "architectural_hotspots": [
    "services/pr_intelligence_service.py"
  ],
  "risk_score": 10.0,
  "improvement_score": 0.0,
  "analyzed_at": "2026-06-20T14:14:00Z"
}
```

---

## Dead Code Intelligence (Phase 2)

### POST /api/dead-code/analyze
Traces reachability from application entry points to sweep unreachable files, orphaned modules, and dead dependency chains.

#### Request Schema (DeadCodeRequest)
- `owner` (string, required): GitHub owner.
- `repo` (string, required): GitHub repo.

```json
{
  "owner": "VarshithReddy2006",
  "repo": "Repo-Intelligence-Agent"
}
```

#### Response (200 OK)
```json
{
  "repo": "VarshithReddy2006/Repo-Intelligence-Agent",
  "cleanup_score": 92,
  "previous_cleanup_score": null,
  "estimated_cleanup_effort": "LOW",
  "unused_files": [
    {
      "file_path": "scripts/unused_script.py",
      "confidence": 0.95,
      "risk_level": "SAFE",
      "recommendation": "Consider removing unused file scripts/unused_script.py"
    }
  ],
  "orphan_modules": [
    {
      "file_path": "services/legacy_helper.py",
      "confidence": 0.90,
      "risk_level": "REVIEW",
      "recommendation": "Review orphaned module services/legacy_helper.py; no active execution path reaches it.",
      "last_reachable_parent": "services/architecture_service.py"
    }
  ],
  "dead_dependency_chains": [
    {
      "chain": ["services/dead_chain_a.py", "services/dead_chain_b.py"],
      "confidence": 0.95,
      "risk_level": "SAFE",
      "recommendation": "Dependency chain [dead_chain_a.py -> dead_chain_b.py] appears unreachable and may be removable as a unit.",
      "length": 1,
      "total_nodes": 2,
      "max_centrality": 0.012
    }
  ],
  "cleanup_recommendations": [
    "Remove unused file scripts/unused_script.py (no active imports).",
    "Review orphaned module services/legacy_helper.py (previously connected via services/architecture_service.py)."
  ],
  "analyzed_at": "2026-06-20T14:14:00Z"
}
```
