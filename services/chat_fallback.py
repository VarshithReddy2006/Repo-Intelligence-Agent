"""Chat Fallback Service.

Generates a retrieval-grounded answer from indexed code chunks when the LLM
provider is unavailable (429 / 5xx / timeout). No LLM call is made — the
retrieved chunks are formatted directly into a readable response.

Used exclusively by backend/api.py chat_streamer() when provider.stream()
raises after exhausting its retry budget.
"""

from typing import List, Dict, Any


def build_fallback_answer(chunks: List[Dict[str, Any]], question: str) -> str:
    """Build a plain-text fallback answer from retrieved chunks.

    Args:
        chunks:   List of Chroma chunk dicts — each has 'content' and
                  'metadata' keys (as returned by chroma_store.search_repository).
        question: The original user question — echoed back for context.

    Returns:
        A formatted string suitable for yielding directly as SSE text tokens.
        Never contains raw HTTP errors, provider names, or exception details.
    """
    if not chunks:
        return (
            "The AI provider is temporarily unavailable and no indexed content "
            "was found for this query.\n\n"
            "Please ensure the repository has been analysed and try again shortly."
        )

    header = (
        "The AI provider is temporarily unavailable. "
        "Here are the most relevant sections from the indexed codebase:\n\n"
    )

    lines: List[str] = [header]

    # Deduplicate by file path — show each file once with its best chunk
    seen_paths: set = set()
    included = 0

    for chunk in chunks:
        meta = chunk.get("metadata", {})
        file_path = meta.get("file_path", "unknown")
        content = chunk.get("content", "").strip()

        if not content or file_path in seen_paths:
            continue

        seen_paths.add(file_path)
        included += 1

        # Truncate long chunks for readability — 600 chars is enough signal
        preview = content[:600]
        if len(content) > 600:
            preview += "\n... [truncated]"

        lines.append(f"📄 **{file_path}**\n```\n{preview}\n```\n")

        # Cap at 4 files to keep the response focused
        if included >= 4:
            break

    if included == 0:
        return (
            "The AI provider is temporarily unavailable and the retrieved chunks "
            "contained no usable content for this query.\n\n"
            "Please try again shortly."
        )

    lines.append(
        "\n---\n"
        "⚠️ *Fallback mode — AI synthesis unavailable. "
        "Showing raw retrieved context only. "
        "Retry your question once the provider recovers.*"
    )

    return "".join(lines)


def is_provider_error(exc: Exception) -> bool:
    """Return True if the exception looks like an LLM provider failure.

    Used to decide whether to trigger fallback mode vs. re-raise for
    unexpected errors (e.g., embedding failures, Chroma errors).
    """
    err_str = str(exc).lower()
    provider_signals = [
        "429",
        "too many requests",
        "rate limit",
        "503",
        "502",
        "500",
        "service unavailable",
        "bad gateway",
        "timeout",
        "connect error",
        "connection refused",
        "nvidia",
        "nim",
        "deepseek",
        "max retries exceeded",
        "statuserror",
    ]
    return any(signal in err_str for signal in provider_signals)
