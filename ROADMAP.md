# Roadmap — Repo Intelligence Agent

This document details the planned milestones, future enhancements, and architectural direction for the Repo Intelligence Agent platform.

Completed work and changelogs for past releases can be found in [CHANGELOG.md](CHANGELOG.md).

---

## v1.1 — Code hygiene Visualizer & Exports (Q3 2026)

Focus on expanding visualization capabilities and rich reporting mechanisms:

- **Dead Code Treemap**: Add a visual tree-map canvas representing code modules sized by line counts and colored by coupling density/orphan status, making hotspots instantly recognizable.
- **Command Palette (`Ctrl+K`)**: Introduce a keyboard-driven command interface on the dashboard to trigger search queries, navigate files, swap views, and clear caches.
- **Rich Document Exports**: Expand download formatting options to support DOCX summaries, customizable charts, and JSON analytics.
- **Extended Language Support**: Incorporate Tree-sitter parsers for C++, Go, and Rust module dependencies.

---

## v1.2 — Multi-Repository Workspaces (Q4 2026)

Cross-codebase search, dependency resolution, and pull request workflows:

- **Cross-Repo Indexing**: Allow developers to load multiple repositories into a single workspace, resolving dependency linkages across microservices.
- **PR Review Assistant**: Integrate GitHub App webhooks to automatically review incoming Pull Requests, post architectural drift reports, and flag circular imports directly inside PR comment threads.
- **Incremental Indexing**: Speed up indexing updates by parsing and vector-storing only modified files on branch updates.

---

## v2.0 — Collaborative Multi-Agent SaaS (2027)

Scaling into a cloud platform for engineering organizations:

- **Collaborative Workspaces**: Multi-user dashboards with code indexing caches, custom team dashboards, and access permission managers.
- **SaaS Platform**: A cloud-hosted version that indexes large enterprise codebases asynchronously.
- **Plugin Ecosystem**: Enable developers to write custom Tree-sitter query modules to check for proprietary coding standards, library replacements, or custom architecture rules.
- **Distributed Agent Teams**: Spawns concurrent, specialized agents (e.g. Ingestion Agent, Refactoring Agent, Documentation Agent) working collaboratively to solve codebase tickets.
