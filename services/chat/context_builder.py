"""Context Builder — Phase 7.

Assembles the final LLM prompt from all intelligence layers, enforcing
a dynamic token budget and structured priority ordering.

Priority order for prompt slots:
  1. System instruction (fixed — not counted in budget)
  2. Architecture context (from ArchContextService)
  3. Structured intelligence (from IntentRouter)
  4. Supporting code chunks (from vector retrieval)
  5. Documentation chunks (README, docs)
  6. Config chunks (pyproject.toml etc.)

Token budget: 3000–5000 tokens target (configurable).
Each "token" is approximated at 4 characters (standard rule of thumb for code).

Output format follows Phase 11 structured answer template injected into
the system instruction so the LLM always produces structured replies.
"""

from __future__ import annotations

import logging
import textwrap
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Token budget constants
# ---------------------------------------------------------------------------

_CHARS_PER_TOKEN = 4          # approximation
_TARGET_MIN_TOKENS = 3_000
_TARGET_MAX_TOKENS = 5_000
_TARGET_MAX_CHARS = _TARGET_MAX_TOKENS * _CHARS_PER_TOKEN   # 20_000 chars
_TARGET_MIN_CHARS = _TARGET_MIN_TOKENS * _CHARS_PER_TOKEN   # 12_000 chars

# Maximum characters for a single chunk to prevent one large file dominating
_MAX_CHUNK_CHARS = 2_000

# System instruction character budget (not counted against context budget)
_SYSTEM_CHARS_EXCLUDED = True


@dataclass
class BuiltContext:
    """Result of context assembly.

    Attributes:
        system_instruction: System instruction for the LLM.
        prompt:             Full assembled prompt (context + question).
        estimated_tokens:   Approximate token count.
        source_files:       All files referenced in the context.
        slot_breakdown:     Per-slot character counts for observability.
    """
    system_instruction: str
    prompt: str
    estimated_tokens: int
    source_files: List[str] = field(default_factory=list)
    slot_breakdown: Dict[str, int] = field(default_factory=dict)


class ContextBuilder:
    """Assembles the LLM prompt from prioritised intelligence slots.

    Usage::

        builder = ContextBuilder()
        ctx = builder.build(
            repo_name="owner/repo",
            question="How does UserService work?",
            arch_context_block="## Architecture ...",
            structured_intelligence="## Symbol Lookup ...",
            code_chunks=[{"content": "...", "metadata": {...}}, ...],
            conversation_history=[{"role": "user", "content": "..."}, ...],
        )
        answer = await provider.generate(
            prompt=ctx.prompt,
            system_instruction=ctx.system_instruction,
            history=ctx.conversation_history,
        )
    """

    def __init__(
        self,
        max_chars: int = _TARGET_MAX_CHARS,
        min_chars: int = _TARGET_MIN_CHARS,
        max_chunk_chars: int = _MAX_CHUNK_CHARS,
    ) -> None:
        self.max_chars = max_chars
        self.min_chars = min_chars
        self.max_chunk_chars = max_chunk_chars

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        repo_name: str,
        question: str,
        arch_context_block: str = "",
        structured_intelligence: str = "",
        code_chunks: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        intent_name: str = "GENERAL_QA",
    ) -> BuiltContext:
        """Assemble the full context prompt.

        Args:
            repo_name:               Repository identifier.
            question:                The (resolved) user question.
            arch_context_block:      Text from ArchContextService.
            structured_intelligence: Text from IntentRouter.
            code_chunks:             Retrieved + reranked code chunks.
            conversation_history:    Prior turns (for history-aware building).
            intent_name:             Detected intent for format tuning.

        Returns:
            BuiltContext with assembled prompt and metadata.
        """
        code_chunks = code_chunks or []
        slots: Dict[str, str] = {}
        breakdown: Dict[str, int] = {}

        # ── Slot 1: Architecture context (highest priority after structure)
        if arch_context_block and arch_context_block.strip():
            slots["architecture"] = arch_context_block.strip()

        # ── Slot 2: Structured intelligence from IntentRouter
        if structured_intelligence and structured_intelligence.strip():
            slots["structured_intelligence"] = structured_intelligence.strip()

        # ── Slot 3: Code chunks (split by tier)
        code_slot, doc_slot, cfg_slot = self._split_chunks_by_tier(code_chunks)
        if code_slot:
            slots["code"] = code_slot
        if doc_slot:
            slots["docs"] = doc_slot
        if cfg_slot:
            slots["config"] = cfg_slot

        # ── Budget enforcement: trim from lowest priority upward
        slots = self._enforce_budget(slots)

        # ── Assemble final prompt
        prompt_parts: List[str] = []

        if "architecture" in slots:
            prompt_parts.append(slots["architecture"])
            breakdown["architecture"] = len(slots["architecture"])

        if "structured_intelligence" in slots:
            prompt_parts.append(
                "## Repository Intelligence\n" + slots["structured_intelligence"]
            )
            breakdown["structured_intelligence"] = len(slots["structured_intelligence"])

        context_parts: List[str] = []
        if "code" in slots:
            context_parts.append(slots["code"])
            breakdown["code"] = len(slots["code"])
        if "docs" in slots:
            context_parts.append(slots["docs"])
            breakdown["docs"] = len(slots["docs"])
        if "config" in slots:
            context_parts.append(slots["config"])
            breakdown["config"] = len(slots["config"])

        if context_parts:
            code_section = "\n\n".join(context_parts)
            prompt_parts.append(
                f"## Repository Code Context — `{repo_name}`\n"
                f"{'=' * 50}\n"
                f"{code_section}\n"
                f"{'=' * 50}"
            )

        prompt_parts.append(f"## Question\n{question}")

        # ── Add suggested next questions hint for the LLM
        prompt_parts.append(
            "## Response Format\n"
            "Structure your response with these sections (use only what is relevant):\n"
            "1. **Summary** — 1–2 sentence direct answer\n"
            "2. **Explanation** — technical detail with file/function references\n"
            "3. **Evidence** — relevant code excerpts (only if present in context above)\n"
            "4. **Repository Insights** — patterns, risks, or architecture notes\n"
            "5. **Relevant Files** — bullet list of key files\n"
            "6. **Suggested Next Questions** — 2–3 natural follow-ups\n\n"
            "Keep code blocks accurate — only show code from the context above."
        )

        prompt = "\n\n".join(prompt_parts)
        estimated_tokens = len(prompt) // _CHARS_PER_TOKEN

        # ── Collect all source files mentioned
        source_files = self._collect_source_files(code_chunks)

        logger.debug(
            "ContextBuilder: slots=%s estimated_tokens=%d",
            list(breakdown.keys()),
            estimated_tokens,
        )

        return BuiltContext(
            system_instruction=self._build_system_instruction(repo_name),
            prompt=prompt,
            estimated_tokens=estimated_tokens,
            source_files=source_files,
            slot_breakdown=breakdown,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_system_instruction(self, repo_name: str) -> str:
        return (
            "You are Repository Intelligence Agent — a Principal Engineer-level assistant "
            f"specialising in the `{repo_name}` codebase.\n\n"
            "RULES:\n"
            "1. Answer ONLY using the repository context provided. Never invent file paths, "
            "class names, or function names not present in the context.\n"
            "2. If context is insufficient, state what was found and what was missing. "
            "Suggest files the user should check.\n"
            "3. You MAY use general programming knowledge to explain language or framework "
            "concepts — but never make repository-specific claims beyond the provided context.\n"
            "4. Always cite specific file paths when making repository-specific statements.\n"
            "5. Keep code snippets accurate — reproduce only what is in the context.\n"
            "6. Never dump hundreds of lines of raw code — summarise and excerpt.\n"
            "7. Produce professional, structured, readable responses."
        )

    def _split_chunks_by_tier(
        self, chunks: List[Dict[str, Any]]
    ) -> tuple[str, str, str]:
        """Split code chunks into code/docs/config text blocks."""
        from .retrieval import _get_tier_weight

        code_blocks: List[str] = []
        doc_blocks: List[str] = []
        cfg_blocks: List[str] = []

        for chunk in chunks:
            meta = chunk.get("metadata", {})
            file_path = meta.get("file_path", "unknown")
            content = chunk.get("content", "").strip()
            if not content:
                continue

            weight = _get_tier_weight(file_path)
            if weight == 0.0:
                # Lockfile / excluded — never include in any slot
                continue

            # Truncate oversized chunks
            if len(content) > self.max_chunk_chars:
                content = content[: self.max_chunk_chars] + "\n... [truncated]"

            score = chunk.get("_rerank_score", 0.0)
            score_label = f" (score: {score:.3f})" if score else ""

            block = (
                f"--- File: `{file_path}`{score_label} ---\n"
                f"```\n{content}\n```"
            )

            weight = _get_tier_weight(file_path)
            if weight >= 1.0:
                code_blocks.append(block)
            elif weight >= 0.5:
                doc_blocks.append(block)
            else:
                cfg_blocks.append(block)

        return (
            "\n\n".join(code_blocks),
            "\n\n".join(doc_blocks),
            "\n\n".join(cfg_blocks),
        )

    def _enforce_budget(self, slots: Dict[str, str]) -> Dict[str, str]:
        """Trim slots to stay within max_chars, removing from lowest priority."""
        priority_order = [
            "architecture",
            "structured_intelligence",
            "code",
            "docs",
            "config",
        ]

        total = sum(len(v) for v in slots.values())
        if total <= self.max_chars:
            return slots

        # Trim from lowest priority first
        for key in reversed(priority_order):
            if total <= self.max_chars:
                break
            if key in slots:
                excess = total - self.max_chars
                current = slots[key]
                if len(current) <= excess:
                    # Remove entire slot
                    total -= len(current)
                    del slots[key]
                    logger.debug("ContextBuilder: removed slot '%s' (budget)", key)
                else:
                    # Truncate
                    slots[key] = current[: len(current) - excess] + "\n... [context trimmed for token budget]"
                    total = sum(len(v) for v in slots.values())
                    logger.debug("ContextBuilder: trimmed slot '%s' (budget)", key)

        return slots

    def _collect_source_files(
        self, chunks: List[Dict[str, Any]]
    ) -> List[str]:
        """Deduplicated list of file paths from chunks."""
        seen: Dict[str, None] = {}
        for chunk in chunks:
            fp = chunk.get("metadata", {}).get("file_path", "")
            if fp:
                seen[fp] = None
        return list(seen.keys())
