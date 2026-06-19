# API Reference Specification

All endpoints are hosted at: `http://localhost:8000`

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
curl http://localhost:8000/health
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
curl http://localhost:8000/api/repos/examples
```

#### Response (200 OK)
```json
[
  {
    "name": "google/guava",
    "url": "https://github.com/google/guava",
    "tech_stack": ["Java", "Maven"],
    "description": "Google core libraries for Java."
  }
]
```

---

### GET /api/repos/recent
Fetch list of repositories processed during the current server session. Note that this collection is kept in-memory and resets on startup.

#### Request Example
```bash
curl http://localhost:8000/api/repos/recent
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
Trigger a full repository cloning, parsing, indexing, and architecture mapping pipeline. This endpoint streams real-time progress tokens using the `text/event-stream` mime-type.

#### Request Schema
```json
{
  "url": "https://github.com/owner/repository",
  "branch": "main",
  "model": "deepseek-ai/deepseek-v4-flash"
}
```

#### Request Example
```bash
curl -N -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "url": "https://github.com/Ankita15k/GitNest",
    "branch": "main"
  }'
```

#### SSE Stream Progression
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
data: {"status": "analyzed", "message": "✓ Architecture analyzed"}
data: {"status": "complete", "message": "✓ Repository analysis complete!"}
data: {"status": "done", "repo": "Ankita15k/GitNest"}
```

---

### POST /api/index
Sync execution endpoint to clone, parse, and embed a repository without generating architecture summaries or dependency graphs. Useful for lightweight Q&A.

#### Request Schema
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

## Semantic Querying

### POST /api/retrieve
Query the vector space index for a particular repository using local semantic embeddings and generate a grounded LLM answer.

#### Request Schema
```json
{
  "repo": "owner/repository",
  "question": "Query text here"
}
```

#### Response (200 OK)
```json
{
  "answer": "Authentication is managed via standard JWT JSON Web Tokens...",
  "sources": [
    {
      "file": "backend/src/controllers/auth.controller.js",
      "content": "const token = jwt.sign({ id: user._id }, process.env.JWT_SECRET... ",
      "score": 0.88
    }
  ]
}
```

---

### POST /api/chat (SSE Stream)
Interactive, conversational multi-turn chat over the repository codebase context, streaming back word tokens.

#### Request Schema
```json
{
  "repo": "owner/repository",
  "message": "User query",
  "history": [
    {"role": "user", "content": "previous question"},
    {"role": "assistant", "content": "previous answer"}
  ]
}
```

#### Request Example
```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "Ankita15k/GitNest",
    "message": "How does Socket.io notify users?",
    "history": []
  }'
```

#### SSE Stream Output
```
data: {"text": "Socket"}
data: {"text": ".io notifications"}
...
data: {"sources": ["backend/src/socket/notificationHandler.js"], "confidence": 92, "status": "done"}
```

---

### POST /api/issues/map
Analyze a GitHub issue and map it to relevant source code modules, generating a detailed implementation plan.

#### Request Schema
```json
{
  "repo": "owner/repository",
  "issue": "Combined issue text (optional)",
  "title": "Issue title (required if issue is omitted)",
  "description": "Issue description text (optional)"
}
```

#### Response (200 OK)
```json
{
  "plan": {
    "title": "Fix token validation timeout",
    "description": "Verify token expiration dates against Redis blocklists.",
    "relevant_files": [
      "backend/src/middleware/authMiddleware.js"
    ],
    "components": ["Authentication"],
    "steps": [
      {
        "step": 1,
        "title": "Update jwt validation checks",
        "file": "backend/src/middleware/authMiddleware.js",
        "description": "Introduce checking of decoded token timestamps against Redis blacklist keys.",
        "type": "modify"
      }
    ]
  },
  "confidence": 88,
  "fallback_used": false
}
```

---

## Architecture Intelligence

### POST /api/architecture/build
Trigger Tree-sitter AST parsing over local cloned repository files and construct the dependency NetworkX graph.

#### Request Schema
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
    "backend/src/index.js",
    "frontend/src/main.jsx"
  ]
}
```

---

### GET /api/architecture/{owner}/{repo_name}
Fetch the generated architecture summary, entry points, and coupling details.

#### Response (200 OK)
```json
{
  "summary": "GitNest is a collaborative coding platform built with the MERN stack...",
  "entry_points": [
    "backend/src/index.js",
    "frontend/src/main.jsx"
  ],
  "core_modules": [
    "backend/src/controllers/auth.controller.js"
  ],
  "high_coupling_modules": [
    "backend/src/controllers/auth.controller.js"
  ],
  "total_files": 328,
  "total_dependencies": 1440
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
      "label": "index.js",
      "type": "module",
      "centrality": 0.95,
      "x": 200,
      "y": 150
    }
  ],
  "edges": [
    {
      "source": "backend/src/index.js",
      "target": "backend/src/app.js",
      "type": "imports"
    }
  ]
}
```

---

### POST /api/reading-order
Generate an optimal, ranked file list for onboarding new developers based on graph centrality metrics.

#### Request Schema
```json
{
  "repo": "owner/repository"
}
```

#### Response (200 OK)
```json
{
  "repo": "Ankita15k/GitNest",
  "reading_order": [
    {
      "rank": 1,
      "file": "backend/src/index.js",
      "reason": "Primary application entry point initializing server configurations.",
      "centrality": 0.95
    }
  ]
}
```

---

### POST /api/impact-analysis
Predict downstream affected modules and components resulting from a proposed change.

#### Request Schema
```json
{
  "repo": "owner/repository",
  "issue": "Proposed modification description"
}
```

#### Response (200 OK)
```json
{
  "repo": "Ankita15k/GitNest",
  "issue": "Modify authentication payload schema",
  "impacted_files": [
    "backend/src/middleware/authMiddleware.js",
    "backend/src/routes/auth.routes.js"
  ],
  "impacted_components": ["Authentication"],
  "risk_level": "high",
  "reasoning": "Modifying the auth payload schema affects all token verification routes and client calls."
}
```
