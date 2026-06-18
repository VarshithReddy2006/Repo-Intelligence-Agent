# Repo Intelligence Agent

![Astro](https://img.shields.io/badge/Frontend-Astro%20%7C%20React%20Islands-FF5D01?style=flat-square&logo=astro&logoColor=white)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/AI%20Layer-Gemini%202.5%20Flash-blue?style=flat-square&logo=googlegemini&logoColor=white)
![ChromaDB](https://img.shields.io/badge/Memory-ChromaDB%20%2B%20SQLite-lightgrey?style=flat-square)
![Pytest](https://img.shields.io/badge/Tests-Pytest-Tests-blue?style=flat-square&logo=pytest)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

> AI-powered repository intelligence platform for understanding, navigating, and planning changes across large codebases.

### What It Does

Repo Intelligence Agent helps developers:

- Understand unfamiliar repositories
- Discover architectural entry points
- Follow guided onboarding paths
- Predict change impact before implementation
- Map issues to relevant code files
- Generate implementation plans with source-backed context

---

## Problem Statement

Repository onboarding is slow because contributors must:
- find entry points and how code paths connect,
- understand architecture before proposing changes,
- map issue text to the relevant files/components,
- and iterate with confidence that proposed changes cover the right areas.

This project indexes repositories, builds architecture and dependency metadata, computes reading paths and impact analysis, and exposes the resulting intelligence through an API (including SSE streaming) and a frontend dashboard.

---

## Key Features

| Category | Capability | Status |
|---|---|---|
| Repository Intelligence | Repository indexing (clone, parse, chunk, embed, store in ChromaDB) | ✅ |
| Repository Intelligence | Retrieval QA (vector search + grounded answers) | ✅ |
| Repository Intelligence | Repository chat with SSE streaming | ✅ |
| Architecture Intelligence | Dependency graph + architecture graph APIs | ✅ |
| Reading Path | Generate onboarding reading paths | ✅ |
| Impact Analysis | Predict affected files/components for a proposed change | ✅ |
| Issue Intelligence | Map issue text to implementation plan / file targets | ✅ |
| Evaluation Layer | Confidence / evaluation integrated into the agent workflow | ✅ |
| Visualizations | React Flow compatible graph output | ✅ |

---

## Architecture Overview

The backend is organized into focused services:

- **GitHub Service** (clone + repo/branch handling)
- **Chunking Service** (code chunking)
- **Embedding Service** (Gemini embeddings; retry support)
- **ChromaDB (Vector Store)** (persisted chunk/vector storage)
- **Retrieval Service** (similarity search + grounded generation)
- **Architecture Service** (architecture metadata + summary persistence)
- **Graph Service** (dependency/graph visualization data for the frontend)
- **Reading Order Service** (reading path generation)
- **Impact Analysis Service** (impact prediction)
- **Issue Mapper + Evaluation Agent** (issue-to-code mapping and confidence/evaluation)

```mermaid
flowchart TB
  U[Developer / API Client] -->|Questions, chats, proposed changes| API[FastAPI Backend API]

  API --> Git[GitHub Service]
  API --> OR[Reading Order Service]
  API --> IA[Impact Analysis Service]
  API --> IMS[Issue Mapper + Evaluation Agent]

  Git --> Parse[Tree-sitter Parsing]
  Parse --> Chunk[Chunking Service]
  Chunk --> Embed[Embedding Service]
  Embed --> Chroma[ChromaDB Vector Store]
  Chroma --> Retrieve[Retrieval Service]
  Retrieve --> Answer[Grounded Answers / Context]

  API --> Arch[Architecture Service]
  Arch --> Summary[Architecture Metadata Summary]
  Arch --> Graph[Graph Service (React Flow data)]
  OR --> ReadingPaths[Reading Path Timeline]
  IA --> Impact[Impact Analysis Results]

  IMS --> Plan[Implementation Targets / Plan Steps]
  Answer --> Stream[SSE Streaming (Analyze / Chat)]
  Plan --> Stream
  Graph --> Frontend[Frontend Dashboard]
  ReadingPaths --> Frontend
  Impact --> Frontend
```

> Note: Features called out as incomplete in `AUDIT_REPORT.md` are not presented here as completed.

---

## Repository Intelligence Workflow

1. Clone repository (GitHub URL / owner+repo)
2. Parse codebase (tree-sitter) and extract relevant structures
3. Chunk source files
4. Generate embeddings
5. Store embeddings in ChromaDB
6. Build dependency graph + architecture metadata
7. Generate reading paths
8. Run impact analysis for a proposed change
9. Answer questions via retrieval (and/or chat)
10. Map issues to implementation targets
11. Evaluate results and provide confidence signals

---

## API Reference

All endpoints below are documented from the routes implemented in `backend/api.py`.

### Indexing / Retrieval
- `POST /api/index`
- `POST /api/retrieve`

### Analysis (SSE streaming)
- `POST /api/analyze`

### Chat (SSE streaming)
- `POST /api/chat`

### Issue Intelligence
- `POST /api/issues/map`

### Reading Path / Impact Analysis
- `POST /api/reading-order`
- `POST /api/impact-analysis`

### Architecture (build + summary + graph)
- `POST /api/architecture/build`
- `GET /api/architecture/{owner}/{repo_name}`
- `GET /api/architecture/{owner}/{repo_name}/graph`

### Repository Examples / Listings / Raw Analysis
- `GET /api/repos/examples`
- `GET /api/repos/recent`
- `GET /api/analysis/{owner}/{repo_name}`

---

## Screenshots

> Placeholders (replace with actual UI captures when available):

- Architecture Graph: `![Architecture Graph](./docs/architecture-graph.png)`
- Reading Path: `![Reading Path](./docs/reading-path.png)`
- Impact Analysis: `![Impact Analysis](./docs/impact-analysis.png)`
- Issue Intelligence: `![Issue Intelligence](./docs/issue-intelligence.png)`
- Repository Chat: `![Repository Chat](./docs/repository-chat.png)`

---

## Validation Results

- Automated test coverage is present in the repository.
- README does not claim exact passing test counts because test execution in this environment failed during collection (vendored dependencies under `data/cloned_repos/` were discovered by pytest).

---

## Roadmap (Not Fully Implemented / Planned)

The following items are explicitly called out as incomplete or not wired in `AUDIT_REPORT.md`:

- Repository Analyzer completion (`agents/analyzer.py` contains TODO / NotImplementedError)
- Architecture Explainer integration (`agents/explainer.py` not wired into active endpoints)
- SQLite metadata persistence layer
- JSON cache layer
- Multi-repository intelligence
- Hybrid retrieval
- Production deployment

---

## Installation

### Backend
```bash
pip install -r requirements.txt
python backend/main.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Contributing

Contributions are welcome. Please open a PR with clear descriptions and test coverage for any changes that affect API schemas, agent behavior, or stored metadata.

---

## License

MIT © 2026 Repo Intelligence Agent
