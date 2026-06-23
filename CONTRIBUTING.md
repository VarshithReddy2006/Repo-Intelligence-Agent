# Contributing to Repo Intelligence Agent

Thank you for your interest in contributing. This guide covers the development workflow, coding standards, testing requirements, and PR process.

---

## Table of Contents

1. [Repository Structure](#repository-structure)
2. [Environment Setup](#environment-setup)
3. [Running Locally](#running-locally)
4. [Coding Standards](#coding-standards)
5. [Testing](#testing)
6. [Adding a New Analysis Service](#adding-a-new-analysis-service)
7. [PR Process](#pr-process)
8. [Issue Reporting](#issue-reporting)
9. [Documentation Standards](#documentation-standards)

---

## Repository Structure

```
backend/          FastAPI app, middleware, routers, settings, dependencies
services/         All business logic (one service per feature domain)
  chat/           Chat v2 pipeline package
  llm/            LLM provider abstraction (Gemini, DeepSeek, factory, errors)
  report/         Report composer and renderers
agents/           IssueMapper (active), EvaluationAgent (active), stubs
core/             Infrastructure: cache, metrics, change detector, DAG registry
memory/           ChromaStore, SQLiteStore stub
models/           Pydantic domain models
storage/          JsonSnapshotStore, SQLite migrations
frontend/         Astro 4 + React dashboard
tests/            535 tests — all must pass before merge
docs/             Extended documentation
```

---

## Environment Setup

```bash
# Clone and enter the project
git clone https://github.com/VarshithReddy2006/Repo-Intelligence-Agent.git
cd Repo-Intelligence-Agent

# Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install in editable mode (registers the repo-intel CLI script)
pip install -e .

# Copy and configure environment
cp .env.example .env
# Edit .env — set LLM_PROVIDER, GEMINI_API_KEY or DEEPSEEK_API_KEY, GITHUB_TOKEN
```

Frontend setup:
```bash
cd frontend
npm install
npm run dev
```

---

## Running Locally

```bash
# Start the backend (port 8001)
python backend/main.py

# Health check
curl http://localhost:8001/health
```

The backend uses `reload_excludes` to filter `data/`, `__pycache__/`, and `tests/` from WatchFiles. This prevents reload loops when repositories are cloned into the data directory.

---

## Coding Standards

**Python**

- Format and lint with Ruff before every commit:
  ```bash
  ruff format .
  ruff check --fix .
  ```
- Use `logging.getLogger(__name__)` — no `print()` statements in production code
- Access all configuration via `backend/settings.settings` — no direct `os.environ.get()` in business logic
- All new API request/response bodies must use Pydantic models
- Keep router files thin — no prompt building, no LLM calls, no retry logic in routers
- All service singletons must be instantiated in `backend/dependencies.py`

**Backward compatibility**

- Do not modify existing API response schemas in a breaking way
- Legacy routes under `/api/` must continue to function alongside `/api/v1/` routes
- New optional fields in request models must have defaults

**Security**

- Never log API key values, tokens, or credentials — log key presence (`bool`) only
- Use parameterized queries for all SQLite operations
- Validate all user-supplied repository URLs through `github_service.parse_repo_url()`

---

## Testing

```bash
# Run the full test suite (always target tests/ explicitly)
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing

# Run a specific file
pytest tests/test_chat.py -v
```

> Do not run `pytest` from the root without a path. It will traverse `data/` and collect import errors from cloned repositories.

**Requirements for all PRs:**

- All 535 existing tests must pass
- New features must include tests covering the happy path and at least one error path
- LLM calls must be mocked — tests must not consume API quota
- GitHub API calls must be mocked — tests must not require a live GitHub token

**Test file naming convention:** `tests/test_<feature>.py`

---

## Adding a New Analysis Service

1. Create `services/my_analysis_service.py` with a class implementing your logic
2. Register it in the DAG in `backend/dependencies.py`:

```python
from services.my_analysis_service import MyAnalysisService

analysis_registry.register(
    "My Analysis",
    MyAnalysisService,
    dependencies=["Symbol Index"],   # runs after Symbol Index completes
    outputs=["my_analysis"]
)
```

3. Instantiate the singleton in `backend/dependencies.py`:

```python
my_analysis_service = MyAnalysisService(...)
```

4. Create a router in `backend/routers/my_analysis.py`
5. Register the router in `backend/api.py` (both root and `/api/v1/` prefix)
6. Add tests in `tests/test_my_analysis.py`
7. Document the endpoint in `docs/API_REFERENCE.md`

The `ExecutionScheduler` will automatically place your task in the correct topological stage. No manual threading or stage management is needed.

---

## PR Process

1. Fork the repository and create a feature branch: `git checkout -b feat/my-feature`
2. Make your changes following the coding standards above
3. Run `ruff format . && ruff check --fix .`
4. Run `pytest tests/ -v` and confirm all tests pass
5. Update `docs/API_REFERENCE.md` if you added or changed endpoints
6. Update `CHANGELOG.md` under an `[Unreleased]` section
7. Open a PR against `main` with:
   - A concise title (< 70 characters)
   - Description summarising what changed, what was tested, and any known limitations
   - Reference to any related issues

**PR checklist:**
- [ ] All tests pass
- [ ] `ruff` reports no errors
- [ ] No hardcoded secrets or credentials
- [ ] Pydantic models used for new request/response bodies
- [ ] `CHANGELOG.md` updated
- [ ] Relevant documentation updated

---

## Issue Reporting

When reporting a bug, include:

- Python version and OS
- Exact error message and stack trace from the backend log
- The repository URL you were analyzing (if applicable)
- Steps to reproduce
- Contents of your `.env` (with API key values redacted)

When requesting a feature, describe:

- The problem you are trying to solve
- How you would expect the feature to behave
- Any existing endpoints or services that could be extended

---

## Documentation Standards

- All public methods must have docstrings with `Args:` and `Returns:` sections
- Markdown files use ATX headings (`#`, `##`) only — no underline style
- Mermaid diagrams must be validated before committing (preview in VS Code or GitHub)
- Documentation must reflect the current implementation — no speculative or future-tense descriptions of existing features
- Do not document roadmap features as if they are already implemented
