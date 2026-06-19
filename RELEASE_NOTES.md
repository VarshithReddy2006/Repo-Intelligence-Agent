# MVP Release Notes (v1.0.0-mvp)

We are proud to announce the initial release of the **Repo Intelligence Agent** MVP. This release delivers a fully functional AI-powered platform for codebase parsing, semantic retrieval, conversational chat, architecture mapping, and issue localization.

---

## 🚀 Key Features Included

- **Full-Pipeline Repository Analysis:** Clones, chunks, embeds, and indexes code codebases, concluding with a comprehensive architecture summary via DeepSeek.
- **Conversational Repository Chat:** Real-time token streaming (SSE) with chat history, local context retrieval, and automatic hallucination scoring.
- **Grounded Issue Mapper:** Maps raw issue texts directly to target code files, generating structured step-by-step implementation plans.
- **Dependency Graph Mapping:** Extracts file dependency structures via AST Tree-sitter parsers and maps module coupling, entry points, and hotspots.
- **Contributor Onboarding Paths:** Generates recommended reading orders based on module NetworkX centrality.
- **Change Impact Analysis:** Predicts downstream file dependencies affected by prospective code changes.

---

## 🛠️ Major Bug Fixes & Hardening

- **DeepSeek & NVIDIA NIM Integration:** Swapped Gemini providers for OpenAI-compatible DeepSeek V4 Flash configurations served via NVIDIA NIM.
- **ChromaDB Vector Integrity:** Fixed dimension mismatch issues on Chroma collection writes by enforcing static 384-dimensional vector schemas.
- **Entry Point Over-Detection:** Patched the entry point detection engine. The parser now excludes tests, docs, and example folders, reducing entry points count on frameworks from ~500 down to the core 17 targets.
- **Issue Mapper Cache Poisoning:** Patched cache collision vulnerability by migrating the memory layer to a `v2:repo:hash` key format, ensuring stale plans do not bleed into current issue mappings.
- **Grounded Fallback Mode:** Added an automatic fallback mechanism for Issue Mapper calls during LLM quota exhaustion, allowing keyword-based component mapping and chunk-content-grounded step generation without crashing.

---

## 📊 Verification & Validation

MVP validation was executed against the **Ankita15k/GitNest** repository:
- **328 files** successfully parsed and mapped.
- **1,549 code chunks** stored and embedded.
- **1,440 dependency edges** mapped.
- Zero code plan hallucinations or path discrepancies observed.
- Backend test coverage exceeding **85%** across all central services.
