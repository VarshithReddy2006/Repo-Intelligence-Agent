# API Reference Specification

All endpoints are hosted at: `http://127.0.0.1:8001`

---

## 🧭 Navigation

- [System Status & Utility](#system-status--utility)
- [Repository Processing](#repository-processing)
- [Semantic Querying](#semantic-querying)
- [Architecture Intelligence](#architecture-intelligence)

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
