# Changelog — Repo Intelligence Agent

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-06-27

### Added
- **Repository Ingestion Pipeline**: Clones public/private repos, detects programming stacks (Python, TypeScript, JavaScript), parses source files via Tree-sitter AST, and builds a NetworkX representation of the dependency graph.
- **Repository Chat (v2)**: Advanced retrieval pipeline that runs a rule-based intent router to categorize queries (Architecture, Dependencies, Churn, Dead Code, Symbol Lookup) and routes them to appropriate AST/graph indices or ChromaDB vector store.
- **Interactive Graphs**: Web portals displaying file-level dependency graphs and function-level call graphs using React Flow and Dagre topological positioning.
- **Repository Health Scorecards**: High-level engineering dashboard rating repositories across Architecture Stability, API Quality, Code Hygiene, Hotspots/Churn, and Onboarding path completeness.
- **VS Code Extension**: Integrates symbol hover cards, CodeLens annotation triggers, inline chats, and webview graphs directly into the IDE.
- **Multi-Provider LLM Orchestration**: Eager startup validation and failover management between Google Gemini (primary) and NVIDIA NIM DeepSeek (fallback) models.

### Changed
- **Scorecard Layout**: Overhauled Health Report scorecard grid into a spacious 4-column layout on desktop to prevent visual clutter and squashed text wrapping.
- **Action Items Restructuring**: Restructured the Health Report page, moving prioritized action items to a balanced 2-column grid at the bottom of the page.

### Improved
- **Floating Controls**: Standardized all React Flow graph actions (Zoom In/Out, Fit, Reset, Center Graph) into unified dark glassmorphic panels.
- **MiniMap Styling**: Updated MiniMaps on both call and dependency graphs to match the dark slate design system.
- **Directory Breadcrumbs**: Integrated segment path breadcrumbs inside the file explorer sidebar preview.
- **Chat Stop/Regenerate Buttons**: Added AbortController integration for canceling long response streams, regeneration actions, and timestamp labels.

### Fixed
- **Scroll Overlap**: Resolved a z-index stacking context bug on the Health Report export footer, forcing scrolling cards to pass cleanly behind the footer panel.
- **Card Height Overflow**: Resolved issues where the bottom borders of critical refactoring issue cards would clip through estimated impacts and recommended fixes.
- **Uvicorn Reload Loop**: Added strict directories and file exclusions to WatchFiles to prevent uvicorn restarts when cloned repository analysis files are written.

### Performance
- **Startup Warmup**: Eagerly pre-loads the BGE embedding model, tokenizer, and Tree-sitter parsers on server initialization to eliminate cold-start latencies.
- **Topological Memoization**: Memoized coordinates calculations on the client-side to prevent unnecessary canvas redraws.

### Developer Experience
- **Ruff Lint Configuration**: Consolidated python style linting and formatting under Ruff.
- **CI/CD Stabilization**: Setup GitHub Actions workflow audits to secure cross-platform execution (Ubuntu/Windows) and Python caches.

### Documentation
- **Consolidated Documentation**: Reorganized scattered guides into 10 structured, root-level markdown documents.
