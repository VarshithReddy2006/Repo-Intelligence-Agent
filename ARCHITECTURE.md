# 🏗️ Architecture Specification

This document provides a comprehensive technical overview of the **Repo Intelligence Agent** system architecture. It outlines the structural layers, data ingestion pipelines, API contracts, mathematical models, and operational workflows.

---

## 🏛️ System Overview & Multi-Layer Design

The application follows a modular, layer-oriented architecture separating the client-side presentation from the local parsing engines and backend intelligence nodes.

```
┌────────────────────────────────────────────────────────┐
│               Astro 4 & React Frontend                 │
│  (Chat Panel, React Flow Visualiser, Reading Timeline)  │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP & SSE (Event Stream)
                            ▼
┌────────────────────────────────────────────────────────┐
│                   FastAPI API Gateway                  │
│  (Binds to Port 8001, SSE Emitters, Request Routing)   │
└───────────────────────────┬────────────────────────────┘
                            │ In-memory & Thread Pools
                            ▼
┌────────────────────────────────────────────────────────┐
│                Code Processing Engine                  │
│  (GitHub Extractor, Code Chunking, Tree-sitter Parser)  │
└─────────────┬─────────────────────────────┬────────────┘
              │                             │
              ▼                             ▼
┌───────────────────────────┐ ┌──────────────────────────┐
│        Data Layer         │ │     Reasoning Layer      │
│  (ChromaDB, NetworkX,     │ │ (DeepSeek V4 Flash NIM)  │
│   analysis_store.json)    │ │                          │
└───────────────────────────┘ └──────────────────────────┘
```

### 1. Client Layer (Astro 4 + React)
- **Astro Pages:** Astro provides zero-JS static structure for routing and layout templates (`index.astro`, `chat.astro`, `analysis.astro`, `issues.astro`).
- **React Hydration:** High-interaction dashboard elements are implemented as React components hydrated in the client browser.
- **Visual Mapping:** Uses `React Flow` to render zoomable, interactive representations of dependency graphs and impact propagation paths.
- **Server-Sent Events (SSE):** Standard HTML5 `EventSource` handles real-time token streaming for chat and indexing logs.

### 2. API Gateway Layer (FastAPI)
- **Asynchronous Execution:** Built on ASGI, utilizing `asyncio` and thread-pool execution (`asyncio.to_thread`) for long-running blocking operations like cloning and embedding generation.
- **Runtime Port:** Serves HTTP traffic on port **8001** (as configured in `backend/main.py` and `frontend/src/lib/api.ts`).
- **Data Integrity:** Employs strictly-typed `Pydantic` models for request validation and response serialization, protecting backend services from malformed payloads.

### 3. Code Ingestion & Processing Layer
- **Extracellular Walk:** Git command-line utility clones repositories locally. The file walker filters out binaries, images, and folders like `.git`, `.venv`, and `node_modules`.
- **AST Parsing:** Tree-sitter runs syntax parsing. It uses compiled language objects for Python, JavaScript, TypeScript, JSX, and TSX to extract imports, exports, class variables, methods, and functions.
- **Code Chunking:** Splits source code into sliding window text blocks (1500 characters, 200 character overlap) to prepare documents for vector indexing.

### 4. Memory & Vector DB Layer (Local)
- **Vector Space:** ChromaDB stores code chunks. Dense representation utilizes `BAAI/bge-small-en-v1.5` loaded locally via `sentence_transformers`. Output vectors are static 384-dimensional arrays.
- **Graph Space:** NetworkX handles directed graph (`DiGraph`) calculations, building import relationships where files represent nodes and imports represent edges.
- **Relational Storage:** Repository metadata and parsed summary schemas are serialized to the local file system at `data/analysis_store.json` on changes, enabling persisted states to survive process recycles.

### 5. AI Reasoning Layer (NVIDIA NIM)
- **Remote Host:** Connects to DeepSeek V4 Flash (`deepseek-ai/deepseek-v4-flash`) hosted on NVIDIA NIM via an OpenAI-compatible interface.
- **Fault Tolerance:** Includes retry policies (exponential backoff) and an automatic fallback mechanism to retrieve and formulate responses locally when API requests fail.

---

## 💾 Unified Workspace & Session Store

The application frontend wraps all repository-specific dashboards inside a **Unified Repository Workspace**.

### 1. Unified Repository Workspace Tabs Layout
```
Unified Repository Workspace
├── CODEBASE ANALYSIS (Overview, Tech Stack, Dependencies, Component Relations)
├── ARCHITECTURE GRAPH (Interactive React Flow Dependency Mapping)
├── READING PATH (Suggested Code Timeline & Centrality Graph)
├── IMPACT ANALYSIS (BFS Traversal Change Predictor)
├── ISSUE INTELLIGENCE (Issue Mapper Plan Generator)
└── CHAT (Context-Grounded Conversational Q&A Panel)
```

The parent `AnalysisDashboard` component fetches the codebase metadata once on initial load, caching it in React state. Switching tabs updates the UI view instantly without invoking re-analysis or repeat backend queries.

### 2. Session Context Sync
To allow seamless workspace sharing and recovery across browser tabs, the active session is divided into two stores:

#### Persisted Session Store (`localStorage`):
- **Fields:** `owner`, `repo`, `indexing status`, `graph status`, and `last analyzed timestamp`.
- **Rationale:** If the user reloads the browser, context is restored instantly. Since the backend persists analysis details to disk, the UI can re-fetch the complete cached analysis from `/api/analysis/{owner}/{repo}` using the stored name, preventing redundant re-clones.

#### Non-persisted Session Store (React In-memory State):
- **Fields:** React Flow graph nodes/edges, file-tree structures, impact analysis BFS paths, and current chat messages.
- **Rationale:** Large graph datasets exceed browser `localStorage` capacity limits (5MB) and degrade browser serialization performance. Storing these in React state keeps memory usage low and page loads fast.

---

## 🛡️ Ingestion Persistence & Chat Fallback

### 1. Ingestion Analysis Persistence Lifecycle
Rather than holding processed analysis logs in volatile memory, the gateway persists state details to `data/analysis_store.json`.
- **Startup Hydration:** On backend startup, FastAPI walks the JSON file and hydrates the `ANALYSIS_STORE` cache.
- **Repository Recovery:** If the FastAPI backend crashes or restarts during local development, already analyzed repositories are recovered instantly without requiring a re-index.
- **Lifecycle Updates:** Any new repository processed via `/api/analyze` triggers an atomic write-back to the JSON file upon completion.

### 2. Chat Fallback Resilience Layer
NVIDIA NIM free-tier API keys are rate-limited to ~3 requests per minute. To maintain a smooth user experience, the `/api/chat` and `/api/issues/map` endpoints implement a fallback structure:

```
                  ┌────────────────────────────────────────┐
                  │          Submit User Request           │
                  └───────────────────┬────────────────────┘
                                      ▼
                  ┌────────────────────────────────────────┐
                  │        Vector ChromaDB Retrieve        │
                  └───────────────────┬────────────────────┘
                                      ▼
                  ┌────────────────────────────────────────┐
                  │    Attempt DeepSeek V4 NIM Call        │
                  └─────────┬────────────────────┬─────────┘
                            │                    │
                    Success │                    │ Rate Limit / 429 / Timeout
                            ▼                    ▼
     ┌──────────────────────────────┐    ┌───────────────────────────────────┐
     │ Stream LLM Tokens to Client  │    │  Activate Grounded Fallback Mode  │
     └──────────────┬───────────────┘    └─────────────────┬─────────────────┘
                    │                                      │
                    │                                      ▼
                    │                    ┌───────────────────────────────────┐
                    │                    │  Fuzzy Match Paths to Components  │
                    │                    └─────────────────┬─────────────────┘
                    │                                      │
                    │                                      ▼
                    │                    ┌───────────────────────────────────┐
                    │                    │ Extract Chunks as Plan Sentences  │
                    │                    └─────────────────┬─────────────────┘
                    │                                      │
                    ▼                                      ▼
     ┌───────────────────────────────────────────────────────────────────────┐
     │          Return Grounded Response + Cited Sources + Confidence         │
     └───────────────────────────────────────────────────────────────────────┘
```

When NVIDIA NIM returns a `429 Too Many Requests` or provider exception:
1. The backend intercepts the exception and suppresses raw HTTP status error traces.
2. It fetches the top-5 relevant code blocks from ChromaDB.
3. It performs local keyword path matching to categorize affected components (e.g. `auth` maps to `Authentication`).
4. It extracts class/function headers from the retrieved code blocks to generate a step-by-step local fallback implementation plan.
5. It outputs the local plan directly to the client alongside ChromaDB source files and a similarity-derived confidence score.

---

## 🧮 Mathematical & Graph Processing Models

### 1. Onboarding Reading Path Heuristics
The Reading Path generator calculates an onboarding hierarchy using structural indicators extracted from the dependency graph. The composite scoring model is defined as:

$$\text{Composite Score}(v) = (W_{\text{entry}} \times \mathbb{I}_{\text{entry}}(v)) + (W_{\text{centrality}} \times C_D(v)) + (W_{\text{in-degree}} \times I_D(v)) + (W_{\text{core}} \times \mathbb{I}_{\text{core}}(v)) - (W_{\text{peripheral}} \times \mathbb{I}_{\text{peripheral}}(v))$$

Where:
- $\mathbb{I}_{\text{entry}}(v) \in \{0, 1\}$ indicates if the node $v$ is a detected framework entry point.
- $C_D(v)$ represents the Normalized Degree Centrality of node $v$ in the undirected representation of the dependency graph:
  $$C_D(v) = \frac{\text{deg}(v)}{N - 1}$$
- $I_D(v)$ represents the Normalized In-Degree of node $v$ (number of other files importing $v$):
  $$I_D(v) = \frac{\text{deg}^-(v)}{N - 1}$$
- $\mathbb{I}_{\text{core}}(v) \in \{0, 1\}$ indicates if the file resides in a core system package (e.g. `services/`, `models/`, `core/`).
- $\mathbb{I}_{\text{peripheral}}(v) \in \{0, 1\}$ indicates if the file is in a non-execution directory (e.g. `tests/`, `docs/`, `examples/`).

#### Scoring Weights configuration:
- $W_{\text{entry}} = 100.0$
- $W_{\text{centrality}} = 50.0$
- $W_{\text{in-degree}} = 30.0$
- $W_{\text{core}} = 15.0$
- $W_{\text{peripheral}} = 100.0$

The service calculates scores, applies topological sorting on the dependency graph to ensure dependencies are read before dependents, and falls back to ordering by composite score descending.

---

### 2. Change Impact Analysis Walk Model
The impact analyzer maps change propagation by walking the directed import graph.
1. **Seed Localization:** Fuzzy matches issue keywords against file paths in the repository to establish the "Seed Set" $S$.
2. **Forward BFS Walk (Direct Dependents):** Traverses edges matching $v \to u$ (where file $u$ imports file $v$) up to depth $4$, mapping immediate downstream dependents.
3. **Reverse BFS Walk (Downstream Dependents):** Traverses backward paths to locate files containing dependencies of the seed files.
4. **Risk Evaluation:** Computes risk score $R$:
   $$R = |F_{\text{affected}}| + (\beta \times |F_{\text{core}}|) + (\gamma \times |F_{\text{coupled}}|)$$
   Where:
   - $F_{\text{affected}}$ is the combined set of directly and indirectly impacted files.
   - $F_{\text{core}}$ is the subset of affected files located in core directories ($\beta = 2$).
   - $F_{\text{coupled}}$ is the subset of affected files having degree centrality higher than average ($\gamma = 1$).
   - **Risk Level:**
     - Low: $R < 4$
     - Medium: $4 \le R < 10$
     - High: $R \ge 10$

---

## 🔌 API Endpoint Specifications

### 🧭 Base URL: `http://127.0.0.1:8001`

| HTTP Method | Path | Request Body | Response Schema | Description |
| :--- | :--- | :--- | :--- | :--- |
| **GET** | `/health` | None | `{backend, llm_provider, llm_model, embedding_provider, vector_db, status}` | Health check |
| **GET** | `/api/repos/examples` | None | `List[{name, url, tech_stack, description}]` | Fetch pre-configured examples |
| **GET** | `/api/repos/recent` | None | `List[{name, url, tech_stack, analyzed_at}]` | List analyzed repositories |
| **POST** | `/api/index` | `{repo_url}` | `{status: "indexed", files: int, chunks: int}` | Index code chunks in ChromaDB |
| **POST** | `/api/analyze` | `{url, branch, model}` | `text/event-stream` (SSE Progress) | Trigger full analysis pipeline |
| **GET** | `/api/analysis/{owner}/{repo_name}` | None | `{analysis: RepositoryAnalysis, architecture: ArchitectureSummary}` | Fetch analysis details |
| **POST** | `/api/issues/map` | `{repo, issue, title, description}` | `IssueMapResponse` | Generate implementation plan |
| **POST** | `/api/chat` | `{repo, message, history: List}` | `text/event-stream` (SSE Chat Tokens) | Streaming chat Q&A |
| **POST** | `/api/architecture/build` | `{repo}` | `{status, repo, files_parsed, dependencies_found, entry_points}` | Rebuild dependency graph |
| **GET** | `/api/architecture/{owner}/{repo_name}` | None | `ArchitectureSummary` | Fetch architecture summary |
| **POST** | `/api/reading-order` | `{repo}` | `ReadingOrder` | Generate onboarding path |
| **POST** | `/api/impact-analysis` | `{repo, issue}` | `ImpactAnalysis` | Predict change impacts |
| **GET** | `/api/architecture/{owner}/{repo_name}/graph` | Query: `q` (filter) | React Flow Node-Link JSON | Fetch dependency graph data |

---

## 🕳️ Skeletal Architectural Stubs

To ensure long-term structure while maintaining local-first MVP operations, the codebase contains four skeletal stubs:

1. **`SQLiteStore` (`memory/sqlite_store.py`):**
   - **Current State:** Skeletal stub raising `NotImplementedError` across all transactional storage calls.
   - **MVP Handling:** In-memory maps and fs-level caching in `data/analysis_store.json` and `data/issue_cache.json` handle state persistence.
2. **`MCPService` (`services/mcp_service.py`):**
   - **Current State:** Skeletal stub raising `NotImplementedError`.
   - **MVP Handling:** Codebase cloning and indexing operations are performed directly via git execution and local walkers.
3. **`RepositoryAnalyzer` (`agents/analyzer.py`):**
   - **Current State:** Skeletal stub raising `NotImplementedError`.
   - **MVP Handling:** Ingestion and stack analysis logic are implemented directly inside `backend/api.py`.
4. **`ArchitectureExplainer` (`agents/explainer.py`):**
   - **Current State:** Skeletal stub raising `NotImplementedError`.
   - **MVP Handling:** Reading order and structural sorting calculations are handled directly inside `services/reading_order_service.py`.
