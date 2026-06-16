# Repo Understanding Agent

> An AI-powered multi-agent system that helps developers understand unfamiliar codebases faster.

## Problem

Developers often spend hours or even days understanding a new repository before they can contribute effectively.

While existing coding assistants are good at answering questions about individual files, understanding an entire repository—including its architecture, dependencies, workflows, and issue impact—remains challenging.

This creates a significant barrier for:

- Open-source contributors
- New team members
- Students learning large projects
- Developers exploring unfamiliar codebases

---

## Solution

Repo Understanding Agent analyzes GitHub repositories and provides actionable insights that help developers understand and navigate codebases more efficiently.

The system can:

- Analyze repository structure
- Explain architecture in plain English
- Identify important files and modules
- Recommend a learning path for new contributors
- Map GitHub issues to relevant files
- Generate implementation plans for features and bug fixes

---

## Key Features

### Repository Analysis

Analyze:

- Directory structure
- Dependencies
- Technologies used
- Repository metadata

### Architecture Understanding

Generate:

- Architecture summaries
- Component relationships
- Dependency overviews
- Suggested reading order

### Issue Mapping

Given a GitHub issue, identify:

- Relevant files
- Affected modules
- Dependencies involved
- Potential implementation steps

### Repository Q&A

Ask questions such as:

> How does authentication work?

> Which files should I modify to add OAuth?

> Where is the API layer implemented?

---

## Agent Architecture

### Repository Analyzer Agent

Responsible for:

- Repository ingestion
- Structure analysis
- Dependency discovery
- Technology stack detection

### Architecture Explainer Agent

Responsible for:

- Architecture summaries
- Component relationship analysis
- Repository walkthroughs

### Issue Mapping Agent

Responsible for:

- GitHub issue analysis
- File relevance prediction
- Implementation planning

### Evaluation Agent

Responsible for:

- Grounding verification
- Hallucination detection
- Confidence scoring

---

## System Architecture

```text
User
  │
  ▼
Antigravity Orchestrator
  │
  ├── Repository Analyzer Agent
  ├── Architecture Explainer Agent
  ├── Issue Mapping Agent
  └── Evaluation Agent
  │
  ▼
Memory Layer
  ├── ChromaDB
  ├── SQLite
  └── Repository Metadata
  │
  ▼
GitHub API / MCP
```

---

## Tech Stack

### AI

- Gemini 2.5 Flash
- Antigravity 2.0

### Repository Access

- GitHub API
- GitHub MCP Server

### Memory

- ChromaDB
- SQLite

### Frontend

- Streamlit

### Deployment

- Google Cloud Run

---

## Roadmap

### Phase 1 – MVP

- [ ] Repository ingestion
- [ ] Repository summary generation
- [ ] Architecture overview
- [ ] Streamlit interface

### Phase 2

- [ ] Repository Q&A
- [ ] File relevance discovery
- [ ] Issue mapping

### Phase 3

- [ ] Persistent memory
- [ ] Multi-agent orchestration
- [ ] Evaluation framework

### Phase 4

- [ ] Deployment
- [ ] User feedback loop
- [ ] Advanced repository reasoning

---

## Example Workflow

### Input

GitHub Repository:

```text
https://github.com/example/project
```

Question:

```text
How does authentication work?
```

### Output

```text
Authentication Flow

Relevant Files:
- auth.py
- middleware.py
- user_service.py

Summary:
Authentication is handled through JWT-based middleware.
The request lifecycle starts in middleware.py and
delegates validation to auth.py.

Suggested Reading Order:
1. auth.py
2. middleware.py
3. user_service.py
```

---

## Future Vision

The long-term goal is to create an intelligent repository companion that can:

- Understand large codebases
- Assist open-source contributors
- Accelerate developer onboarding
- Bridge the gap between repository exploration and implementation

---

## Project Status

🚧 Currently under development as part of Kaggle's

**5-Day AI Agents: Intensive Vibe Coding Course with Google**

---

## License

MIT License
