# Repo Understanding Agent

An AI-powered multi-agent system that helps developers understand unfamiliar codebases faster.

## Problem

Developers often spend hours or days understanding a new repository before they can contribute effectively.

Existing tools are good at explaining individual files, but understanding repository architecture, dependencies, and issue impact remains difficult.

## Solution

Repo Understanding Agent analyzes repositories and helps developers:

* Understand repository architecture
* Discover important files and modules
* Learn repository structure faster
* Map GitHub issues to relevant files
* Generate implementation plans for new features and bug fixes

## Planned Agent Architecture

### Repository Analyzer Agent

Analyzes repository structure, dependencies, and file relationships.

### Architecture Explainer Agent

Generates human-readable explanations of repository architecture.

### Issue Mapping Agent

Maps GitHub issues to likely affected files and modules.

### Evaluation Agent

Validates explanations and implementation plans against repository evidence.

## Roadmap

### Phase 1

* Repository ingestion
* Repository summaries
* Architecture overview generation

### Phase 2

* Repository Q&A
* Issue-to-file mapping

### Phase 3

* Memory layer
* Multi-agent orchestration

### Phase 4

* Evaluation framework
* Deployment

## Tech Stack

* Antigravity 2.0
* Gemini
* MCP
* GitHub APIs

## Status

Currently under development as part of Kaggle's 5-Day AI Agents: Intensive Vibe Coding Course with Google.
