# Repo Intelligence Agent

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue?style=for-the-badge" alt="v1.0.0"/>
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Frontend-Astro%204%20%2B%20React-FF5D01?style=for-the-badge&logo=astro&logoColor=white" alt="Astro + React"/>
  <img src="https://img.shields.io/badge/LLM-Gemini%202.5%20Flash-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Gemini"/>
  <img src="https://img.shields.io/badge/LLM-DeepSeek%20V4%20Flash-6C5CE7?style=for-the-badge" alt="DeepSeek V4 Flash"/>
  <img src="https://img.shields.io/badge/Vector%20DB-ChromaDB-blue?style=for-the-badge" alt="ChromaDB"/>
  <img src="https://img.shields.io/badge/AST%20Parser-Tree--sitter-black?style=for-the-badge" alt="Tree-sitter"/>
  <img src="https://img.shields.io/badge/Tests-535%20passing-brightgreen?style=for-the-badge" alt="535 tests"/>
</p>

<p align="center">
  <strong>A production-grade codebase intelligence platform. It combines AST structural parsing, NetworkX dependency graphs, multi-provider LLM reasoning, and a full retrieval pipeline to deliver repository chat, architecture analysis, PR risk assessment, dead code detection, and a unified health report.</strong>
</p>

<p align="center">
  <a href="#motivation">Motivation</a> •
  <a href="#features">Features</a> •
  <a href="#architecture-overview">Architecture</a> •
  <a href="#installation">Installation</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#running-locally">Running Locally</a> •
  <a href="#api-reference">API Reference</a> •
  <a href="#testing">Testing</a> •
  <a href="#security">Security</a> •
  <a href="#contributing">Contributing</a> •
  <a href="ARCHITECTURE.md">Full Architecture Spec</a>
</p>

---

## Motivation

Traditional codebase assistants rely on unstructured vector similarity:

```
Traditional RAG:  Repo → Text Split → Embeddings → Similarity Search → LLM
```

This approach is blind to code structure, import graphs, coupling, and execution entry points. It hallucinates dependencies and misses downstream side effects.

**Repo Intelligence Agent** takes a structural approach:

```
Repo
  ├── Tree-sitter AST Parser ──→ Imports, Exports, Symbols
  │                                        │
  │                              NetworkX DiGraph
  │                                        │
  ├── ChromaDB (BGE embeddings) ──→ Semantic search
  ├── Centrality analytics ──────→ Reading order
  └── BFS traversals ──────────→ Impact & blast radius
                                         │
                          Gemini 2.5 Flash / DeepSeek V4 Flash
                                         │
                              Grounded code intelligence
```

---

## Features

### Repository Intelligence Report (v3.0)
The flagship feature. Aggregates all analysis outputs into a single health report scored across five dimensions: Architecture Stability, API Quality, Code Hygiene, Hotspot Risk, and Onboarding Clarity. Exported as interactive HTML, print-optimized PDF, or collapsible Markdown for GitHub PR comments.

### Repository Chat (v2)
Full intelligence layer over any indexed repository. Nine intent types are detected by a rule-based classifier (zero LLM calls), then routed to structured services before hitting the vector retrieval pipeline. Streams token-by-token via SSE. Includes circuit breaker failover and a professional fallback renderer when no provider is available.

### Repository Analysis Pipeline
Clones any public GitHub repository, runs Tree-sitter AST parsing, generates BGE embeddings, indexes in ChromaDB, builds a NetworkX dependency graph, and computes an architecture summary. Supports incremental rebuilds — only changed files are re-processed.

### Architecture Graph
Interactive React Flow dependency graph with search filtering, neighborhood inspection, and forward/backward BFS reachability traces.

### Call Graph Intelligence
Function-level call graph built from AST analysis. Supports callers, callees, hierarchy walks, blast-radius estimation, and BFS traces.

### API Surface Intelligence
Classifies every exported symbol as public, internal, or deprecated. Computes Martin's instability metrics and detects breaking changes between repository versions.

### Git History & Churn Analysis
Mines git commit history to compute per-file churn scores. Identifies hotspot files (high churn + high coupling) and produces weekly activity timelines.

### PR Intelligence & Architecture Drift
Risk-scores pull requests by size (XS–XL), blast radius (LOW–EXTREME), and symbol diffs. Detects architectural drift by virtual delta-patching the dependency graph against the PR's changed files.

### Dead Code Detection
Reachability sweep from entry points across the dependency graph. Identifies unused files, orphaned modules, and dead dependency chains with a weighted cleanup score (0–100).

### Issue Mapper
Maps GitHub issues to relevant source files using two LLM calls: one to parse and rank, one to generate a grounded implementation plan. Uses embedding retrieval and caching to avoid redundant API calls.

### Symbol Intelligence
AST-extracted symbol index (classes, functions, methods) per repository. Supports definition lookup and cross-file reference search.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              Astro 4 + React Dashboard                  │
│  (Chat, React Flow Graphs, Reading Timeline, Reports)   │
└────────────────────────┬────────────────────────────────┘
                         │  HTTP + SSE
                         ▼
┌─────────────────────────────────────────────────────────┐
│             FastAPI Gateway  (port 8001)                │
│  RateLimitMiddleware · GZip · CORS · RequestId · Metrics│
└───────────┬────────────────────────────────┬────────────┘
            │                                │
            ▼                                ▼
┌───────────────────────┐      ┌─────────────────────────┐
│  Code Ingestion Layer │      │   Chat Pipeline (v2)    │
│  GitHub Clone         │      │   Intent Detector       │
│  Tree-sitter AST      │      │   Intent Router         │
│  Code Chunking        │      │   Retrieval (BGE+rerank) │
│  BGE Embeddings       │      │   ProviderManager       │
│  ChromaDB Index       │      │   Circuit Breaker       │
│  NetworkX Graph       │      │   Fallback Renderer     │
└───────────┬───────────┘      └────────────┬────────────┘
            │                               │
            ▼                               ▼
┌─────────────────────────────────────────────────────────┐
│                    Data Layer                           │
│  ChromaDB · NetworkX Graphs · Symbol Index              │
│  SQLite (reports, migrations) · JSON Snapshot Store     │
│  Analysis Cache (in-memory, schema-versioned)           │
└─────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────┐
│             LLM Reasoning Layer                         │
│  Primary: Gemini 2.5 Flash  (google-genai SDK)          │
│  Fallback: DeepSeek V4 Flash (NVIDIA NIM / OpenAI API)  │
│  Circuit breaker · exponential backoff · health checks  │
└─────────────────────────────────────────────────────────┘
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for full component diagrams, math models, and sequence diagrams.

---

## Installation

### Prerequisites

- Python 3.10, 3.11, or 3.12
- Node.js 18+ (for the frontend)
- Git
- A Google Gemini API key **or** an NVIDIA NIM API key (for DeepSeek)
- ~2 GB disk space for the BGE embedding model cache

### Backend setup

```bash
# Clone the repository
git clone https://github.com/VarshithReddy2006/Repo-Intelligence-Agent.git
cd Repo-Intelligence-Agent

# Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install the package and CLI
pip install -e .
```

### Frontend setup

```bash
cd frontend
npm install
npm run dev   # development server at http://localhost:4321
```

---

## Configuration

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_PROVIDER` | Yes | `gemini` | Active LLM provider: `gemini` or `deepseek` |
| `GEMINI_API_KEY` | When `LLM_PROVIDER=gemini` | — | Google AI Studio Developer API key |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model variant |
| `DEEPSEEK_API_KEY` | When `LLM_PROVIDER=deepseek` | — | NVIDIA NIM API key |
| `DEEPSEEK_BASE_URL` | No | `https://integrate.api.nvidia.com/v1` | NVIDIA NIM base URL |
| `DEEPSEEK_MODEL` | No | `deepseek-ai/deepseek-v4-flash` | DeepSeek model variant |
| `GITHUB_TOKEN` | Recommended | — | GitHub PAT for cloning and API access |
| `API_SERVER_HOST` | No | `0.0.0.0` | Uvicorn bind host |
| `API_SERVER_PORT` | No | `8001` | Uvicorn bind port |
| `FRONTEND_URL` | No | `http://localhost:4321` | Allowed CORS origin |
| `SQLITE_DB_PATH` | No | `data/repo_understanding.db` | SQLite database path |
| `CHROMA_DB_PATH` | No | `data/chroma_db` | ChromaDB persistence directory |
| `CLONED_REPOS_PATH` | Recommended | `~/.repo_intelligence/cloned_repos` | Clone destination. Must be outside the project tree to avoid triggering uvicorn reload. |
| `APP_ENV` | No | `development` | `development` or `production`. Controls startup fail-fast behavior. |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `LOG_FORMAT` | No | `human` | `human` or `json` (use `json` in production) |
| `RATE_LIMIT_PER_MINUTE` | No | `60` | Max requests per IP per minute |
| `ALLOWED_HOSTS` | No | `["*"]` | TrustedHost middleware allowed hostnames |

---

## Running Locally

### Start the backend

```bash
python backend/main.py
```

The server starts on `http://localhost:8001`. Interactive API docs are at `http://localhost:8001/docs`.

### Start the frontend

```bash
cd frontend
npm run dev
```

Open `http://localhost:4321` in your browser.

### Verify health

```bash
curl http://localhost:8001/health
```

Expected response:
```json
{
  "backend": "online",
  "llm_provider": "gemini",
  "llm_model": "gemini-2.5-flash",
  "embedding_provider": "BAAI/bge-small-en-v1.5",
  "vector_db": "chromadb",
  "status": "healthy"
}
```

---

## Docker

### Production

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Mounts named volumes for `data/` (ChromaDB, graphs, SQLite) and the cloned repository cache.

### Development (hot reload)

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

---

## Repository Analysis

Analyze any public GitHub repository:

```bash
# Via CLI
repo-intel analyze https://github.com/fastapi/fastapi

# Via API (streams SSE progress)
curl -N -X POST http://localhost:8001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/fastapi/fastapi", "branch": "master"}'
```

The pipeline stages: clone → detect tech stack → chunk → embed → index ChromaDB → build symbol index → build dependency graph → build call graph → compute API surface → generate architecture summary.

Subsequent analyses of the same repository are incremental: only changed files are re-processed.

---

## Repository Chat

```bash
curl -N -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "fastapi/fastapi",
    "message": "How is dependency injection implemented?",
    "history": []
  }'
```

Streams token-by-token SSE. The v2 pipeline runs intent detection, routes to structured intelligence services, then retrieves and reranks the top-15 chunks to top-5 before calling the LLM.

Check provider health:

```bash
curl http://localhost:8001/api/chat/health
```

Hot-reload the LLM provider after updating `.env`:

```bash
curl -X POST http://localhost:8001/api/chat/reload
```

---

## Streaming Chat

Every streaming endpoint returns `text/event-stream` SSE. The final event always includes `"status": "done"`. Chat responses also include a `sources` array with cited file paths and a `confidence` score.

For provider failover: if the primary provider's circuit breaker opens (3 failures), the `ProviderManager` automatically switches to the secondary provider. If both are unavailable, the `FallbackRenderer` returns a structured retrieval-grounded response without calling any LLM.

---

## Repository Intelligence Report

Generate and download the unified health report for any analyzed repository:

```bash
# CLI
repo-intel report fastapi/fastapi
repo-intel report fastapi/fastapi --markdown
repo-intel report fastapi/fastapi --pdf -o report.html

# API — build and return full report model
curl -X POST http://localhost:8001/api/v1/report/fastapi/fastapi/build

# API — download HTML report
curl -o report.html "http://localhost:8001/api/v1/report/fastapi/fastapi/download?format=html"

# API — download Markdown (for PR comments)
curl -o report.md "http://localhost:8001/api/v1/report/fastapi/fastapi/download?format=markdown"
```

---

## API Reference

All endpoints are available at `http://localhost:8001` and mirrored under `/api/v1/` for versioned access.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | System health and active provider |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/api/repos/examples` | Pre-configured example repositories |
| `GET` | `/api/repos/recent` | Recently analyzed repositories |
| `POST` | `/api/analyze` | Full analysis pipeline (SSE) |
| `POST` | `/api/index` | Vector-only indexing |
| `GET` | `/api/analysis/{owner}/{repo}` | Fetch analysis result |
| `POST` | `/api/repos/repair` | Rebuild missing symbol/graph indexes |
| `POST` | `/api/retrieve` | Vector search + LLM answer |
| `POST` | `/api/chat` | Streaming repository chat (SSE) |
| `GET` | `/api/chat/health` | Provider health diagnostic |
| `POST` | `/api/chat/reload` | Hot-reload LLM provider |
| `POST` | `/api/issues/map` | Map GitHub issue to implementation plan |
| `POST` | `/api/architecture/build` | Build dependency graph |
| `GET` | `/api/architecture/{owner}/{repo}` | Architecture summary |
| `GET` | `/api/architecture/{owner}/{repo}/graph` | React Flow dependency graph |
| `POST` | `/api/reading-order` | Onboarding reading order |
| `POST` | `/api/impact-analysis` | Change impact prediction |
| `GET` | `/api/graph/{owner}/{repo}/full` | Full interactive graph |
| `GET` | `/api/graph/{owner}/{repo}/neighbors/{path}` | Node neighborhood |
| `GET` | `/api/graph/{owner}/{repo}/trace/{path}` | BFS trace |
| `GET` | `/api/graph/{owner}/{repo}/search` | Graph node search |
| `GET` | `/api/symbols/{owner}/{repo}/file/{path}` | Symbols in file |
| `GET` | `/api/symbols/{owner}/{repo}/definition/{name}` | Symbol definition |
| `GET` | `/api/symbols/{owner}/{repo}/references/{name}` | Symbol references |
| `POST` | `/api/call-graph/build` | Build call graph (SSE) |
| `GET` | `/api/call-graph/{owner}/{repo}` | React Flow call graph |
| `GET` | `/api/call-graph/{owner}/{repo}/callers/{fn}` | Callers of a function |
| `GET` | `/api/call-graph/{owner}/{repo}/callees/{fn}` | Callees of a function |
| `GET` | `/api/call-graph/{owner}/{repo}/blast-radius/{fn}` | Function blast radius |
| `POST` | `/api/api-surface/build` | Build API surface index (SSE) |
| `GET` | `/api/api-surface/{owner}/{repo}` | Full API surface report |
| `GET` | `/api/api-surface/{owner}/{repo}/public` | Public symbols |
| `GET` | `/api/api-surface/{owner}/{repo}/breaking` | Breaking changes |
| `POST` | `/api/churn/analyze` | Mine git history (SSE) |
| `GET` | `/api/churn/{owner}/{repo}` | Churn summary |
| `GET` | `/api/churn/{owner}/{repo}/hotspots` | Top hotspot files |
| `POST` | `/api/pr/analyze` | PR risk and blast radius |
| `GET` | `/api/pr/health` | PR intelligence diagnostics |
| `POST` | `/api/architecture/drift` | Architecture drift detection |
| `POST` | `/api/dead-code/analyze` | Dead code sweep |
| `POST` | `/api/v1/report/{owner}/{repo}/build` | Build intelligence report |
| `GET` | `/api/v1/report/{owner}/{repo}/summary` | Report health summary |
| `GET` | `/api/v1/report/{owner}/{repo}/download` | Download HTML/PDF/Markdown |

Full request/response documentation: [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

---

## Project Structure

```
Repo-Intelligence-Agent/
├── backend/                    # FastAPI application
│   ├── api.py                  # App factory, middleware, router registration, startup
│   ├── main.py                 # Uvicorn entry point with watch-dir filtering
│   ├── settings.py             # Pydantic Settings (all env vars)
│   ├── dependencies.py         # Service singletons and analysis store
│   ├── security_middleware.py  # Rate limiting (sliding window per IP)
│   ├── logging_middleware.py   # Request ID injection
│   ├── metrics_middleware.py   # Prometheus metrics collection
│   └── routers/                # One router per feature domain
├── services/                   # All business logic
│   ├── chat/                   # Chat v2 pipeline package
│   │   ├── retrieval_pipeline.py  # Authoritative pipeline
│   │   ├── intent_detector.py     # Rule-based, 9 intents
│   │   ├── intent_router.py       # Routes to structured services
│   │   ├── conversation_memory.py # Session memory, pronoun resolution
│   │   ├── retrieval.py           # Tier-weighted reranking
│   │   ├── context_builder.py     # Token budgeting
│   │   ├── provider_manager.py    # Circuit breaker + failover
│   │   └── fallback_renderer.py   # Professional fallback UX
│   ├── llm/                    # LLM provider abstraction
│   │   ├── base_provider.py    # Abstract interface + ProviderHealth
│   │   ├── gemini_provider.py  # Gemini 2.5 Flash
│   │   ├── deepseek_provider.py # DeepSeek V4 Flash (NVIDIA NIM)
│   │   ├── provider_factory.py  # Singleton + hot-reload + validation
│   │   └── provider_errors.py  # Error classification
│   ├── report/                 # Report generation
│   │   ├── composer.py         # Assembles ReportDataModel
│   │   └── renderer.py         # HTML, Markdown, PDF renderers
│   └── *.py                    # Architecture, graph, symbol, PR, drift, etc.
├── agents/                     # Agent classes (IssueMapper, EvaluationAgent active)
├── core/                       # Infrastructure
│   ├── cache.py                # Schema-versioned in-memory cache
│   ├── metrics.py              # Prometheus registry
│   ├── repository_context.py   # Lazy-loaded repo state
│   ├── change_detector.py      # File hash-based change detection
│   ├── analysis_registry.py    # DAG task registry
│   └── build_pipeline.py       # DAG orchestration
├── memory/                     # Storage adapters (ChromaStore)
├── models/                     # Pydantic domain models
├── storage/                    # JsonSnapshotStore, SQLite migrations
├── frontend/                   # Astro 4 + React dashboard
├── tests/                      # 535 passing tests
├── docs/                       # Extended documentation
└── .env.example                # Environment template
```

---

## Performance

| Operation | Typical Duration |
|---|---|
| Fresh repository analysis (small, ~300 files) | ~25–45 s |
| Incremental rebuild (small change set) | < 2 s |
| Chat first token | < 3 s |
| Chat streaming latency | ~50–90 ms/token |
| Architecture graph build | ~1.8 s |
| PR analysis | ~1.5 s |

Prometheus metrics on `/metrics`:
- `http_requests_total` — request counts by method, path, status
- `active_requests_count` — in-flight requests gauge
- `build_duration_seconds` — per-repository build durations
- `analysis_task_duration_seconds` — per-task durations
- `cache_hits_total` / `cache_misses_total` — cache efficiency

---

## Security

- **Rate limiting**: 60 requests/minute per IP by default (configurable via `RATE_LIMIT_PER_MINUTE`)
- **CORS**: Restricted to `FRONTEND_URL` — set this to your production domain in production
- **Input validation**: Pydantic on every request body
- **Secrets**: API keys loaded exclusively from environment variables, never logged
- **LLM auth hardening**: All providers are health-checked at startup. Invalid credentials cause a fail-fast in production mode with actionable error messages
- **Rate limit bypass**: `/health` and `/metrics` are exempt from rate limiting
- **No user authentication**: This is a public API. Add a reverse proxy with auth for multi-tenant deployments

See [SECURITY.md](SECURITY.md) for responsible disclosure details.

---

## Testing

```bash
# Run the full test suite
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing
```

535 tests across unit, integration, and service-layer categories. Mock adapters isolate LLM and GitHub API boundaries so tests run without consuming API quota.

> Always target `pytest tests/` — running `pytest` from the repo root will traverse `data/` and fail on import errors from cloned repositories.

---

## Production Readiness

- **Overall score: 92/100** (audited June 2026)
- Zero P0/P1 blocking issues
- Circuit breaker failover: Gemini → DeepSeek → Fallback Mode
- Structured JSON logging with request IDs
- Prometheus metrics endpoint
- Startup provider validation (fail-fast in production)
- Incremental build manifests with schema versioning
- Atomic file operations for analysis store persistence

See [docs/production.md](docs/production.md) for the full production operations guide.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow, coding standards, and PR guidelines.

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/) for the async API framework
- [Astro](https://astro.build/) for the frontend framework
- [ChromaDB](https://www.trychroma.com/) for local vector storage
- [sentence-transformers](https://www.sbert.net/) for BGE embeddings
- [tree-sitter](https://tree-sitter.github.io/tree-sitter/) for AST parsing
- [NetworkX](https://networkx.org/) for graph algorithms
- Google Gemini and NVIDIA NIM for LLM inference
