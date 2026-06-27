# API Reference Guide — Repo Intelligence Agent v1.0

This document details the REST endpoints and Server-Sent Event (SSE) streams exposed by the FastAPI backend server. 

All endpoints are versioned under the `/api/v1` prefix. Legacy root paths (e.g. `/api/...`) are supported as backward-compatible shims.

---

## 1. Repository Ingestion & Analysis

### Index Repository (Sync)
Triggers synchronous metadata ingestion for a repository.

- **Endpoint**: `POST /api/v1/index`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "repo_url": "https://github.com/fastapi/fastapi",
    "branch": "master"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "status": "completed",
    "owner": "fastapi",
    "repo_name": "fastapi",
    "files_count": 342,
    "symbols_count": 1821
  }
  ```

---

### Index Repository (Streaming Analysis)
Triggers repository cloning and AST parsing, streaming progress updates as Server-Sent Events (SSE).

- **Endpoint**: `POST /api/v1/analyze`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "repo_url": "https://github.com/fastapi/fastapi",
    "branch": "master"
  }
  ```
- **SSE Stream Data (Progress Events)**:
  ```text
  event: progress
  data: {"status": "cloning", "percent": 15, "message": "Cloning repository..."}

  event: progress
  data: {"status": "parsing", "percent": 50, "message": "Parsing abstract syntax trees..."}

  event: progress
  data: {"status": "completed", "percent": 100, "message": "Analysis completed."}
  ```
- **Error Response (400 Bad Request / 404 Not Found)**:
  If the repository is not found or invalid, returns an error event and closes the connection:
  ```text
  event: error
  data: {"stage": "Cloning", "reason": "Repository not found or private.", "suggested_fix": "Verify repository is public or supply GITHUB_TOKEN."}
  ```

---

### Get Ingested Analysis Details
Returns metadata for an already analyzed repository.

- **Endpoint**: `GET /api/v1/analysis/{owner}/{repo_name}`
- **Method**: `GET`
- **Response (200 OK)**:
  ```json
  {
    "owner": "fastapi",
    "repo_name": "fastapi",
    "indexed_at": "2026-06-27T12:00:00Z",
    "primary_language": "Python",
    "files_indexed": 342,
    "status": "ready"
  }
  ```

---

## 2. Codebase Chat Engine

### Chat Query (Streaming)
Queries the multi-agent chatbot about the codebase. Responses are streamed as SSE chunks.

- **Endpoint**: `POST /api/v1/chat`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "repo": "fastapi/fastapi",
    "message": "What is the entry point of the app?",
    "history": [
      {"role": "user", "content": "Hi"},
      {"role": "assistant", "content": "Hello! How can I help?"}
    ]
  }
  ```
- **Headers Required**: `Accept: text/event-stream`
- **SSE Stream Data Chunks**:
  ```text
  event: chunk
  data: "The "

  event: chunk
  data: "main "

  event: chunk
  data: "entrypoint "

  event: citations
  data: [{"file": "fastapi/main.py", "lines": "1-15", "confidence": 0.95}]

  event: done
  data: [DONE]
  ```

---

## 3. Visualizations & Graphs

### Get File Dependency Graph
Returns node and edge representations for the file-level import graph.

- **Endpoint**: `GET /api/v1/graph/{owner}/{repo}/full`
- **Method**: `GET`
- **Query Parameters**:
  - `q`: Optional search keyword to filter nodes.
- **Response (200 OK)**:
  ```json
  {
    "nodes": [
      {
        "id": "fastapi/main.py",
        "label": "main.py",
        "category": "entry_point",
        "highlighted": false,
        "is_focus": false
      }
    ],
    "edges": [
      {
        "source": "fastapi/main.py",
        "target": "fastapi/applications.py",
        "relationship": "imports"
      }
    ],
    "matched_count": 1
  }
  ```

---

### Get Neighborhood Subgraph
Returns only the immediate imports and dependents of a focus node.

- **Endpoint**: `GET /api/v1/graph/{owner}/{repo}/neighbors/{focus_id}`
- **Method**: `GET`
- **Response (200 OK)**:
  *(Same schema format as full graph, filtered to neighborhood nodes)*

---

### Trace Paths (Reachability/Blast Radius)
Computes a reachability subgraph using BFS in forward, backward, or bidirectional orientations.

- **Endpoint**: `GET /api/v1/graph/{owner}/{repo}/trace/{focus_id}`
- **Method**: `GET`
- **Query Parameters**:
  - `direction`: `forward` (imports), `backward` (dependents), or `both`.
  - `depth`: Maximum depth search limit (default `6`).
- **Response (200 OK)**:
  *(Returns sub-graph representing reachability paths)*

---

## 4. Reports & Engineering Audits

### Compile Health Report
Triggers report generation or fetches the cached analysis report.

- **Endpoint**: `POST /api/v1/report/{owner}/{repo}/build`
- **Method**: `POST`
- **Response (200 OK)**:
  ```json
  {
    "metadata": {
      "repo_name": "fastapi",
      "owner": "fastapi",
      "total_loc": 25410,
      "generated_at": "2026-06-27T18:00:00Z"
    },
    "scores": {
      "overall": 88,
      "architecture": 90,
      "api": 85,
      "hygiene": 92,
      "churn": 80,
      "readability": 95,
      "grade": "A"
    },
    "refactoring_priorities": [
      "Refactor volatile hotspot module: fastapi/applications.py (churn score: 95.0)"
    ]
  }
  ```

---

### Download Report Files
Downloads the report in static formats.

- **Endpoint**: `GET /api/v1/report/{owner}/{repo}/download`
- **Method**: `GET`
- **Query Parameters**:
  - `format`: `html`, `markdown`, or `pdf`.
- **Response**: File attachment stream (`text/html`, `text/markdown`, or `application/pdf`).

---

## 5. Health & Server Status

### Server Live Status
- **Endpoint**: `GET /health` (or `/api/v1/health`)
- **Method**: `GET`
- **Response (200 OK)**:
  ```json
  {
    "status": "healthy",
    "env": "development",
    "uptime_seconds": 3600
  }
  ```
