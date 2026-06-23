"""Intelligent Retrieval — Phases 5 & 6.

Improvements over the original flat top-5 search:
  - Lockfile / generated file exclusion (Tier 4 weight = 0, never retrieved)
  - Repository-aware tier weighting applied to distances
  - Asymmetric BGE query prefix ("Represent this sentence for searching…")
  - Top-15 → rerank → deduplicate → top-5 pipeline
  - Chunk deduplication: identical content hashes are collapsed

Tier weights
------------
  Tier 1 (1.0): backend/, services/, routers/, models/, frontend/src/
  Tier 2 (0.6): README, docs/
  Tier 3 (0.2): requirements.txt, package.json, pyproject.toml, *.toml, *.cfg
  Tier 4 (0.0): lock files, node_modules/, dist/, coverage/, vendor/, *.min.js

Reranker
--------
  Simple cross-encoder approximation using token overlap between the query
  and the chunk content. No external model required — fast, deterministic,
  zero latency overhead from model loading.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tier weights and exclusion patterns
# ---------------------------------------------------------------------------

# Files matching these patterns are EXCLUDED from retrieval entirely (weight 0)
_EXCLUDED_PATTERNS: List[re.Pattern] = [
    re.compile(r"package-lock\.json$", re.I),
    re.compile(r"pnpm-lock\.yaml$", re.I),
    re.compile(r"yarn\.lock$", re.I),
    re.compile(r"composer\.lock$", re.I),
    re.compile(r"Gemfile\.lock$", re.I),
    re.compile(r"Cargo\.lock$", re.I),
    re.compile(r"poetry\.lock$", re.I),
    re.compile(r"\.lock$", re.I),
    re.compile(r"node_modules[/\\]", re.I),
    re.compile(r"[/\\]dist[/\\]", re.I),
    re.compile(r"[/\\]build[/\\]", re.I),
    re.compile(r"[/\\]coverage[/\\]", re.I),
    re.compile(r"[/\\]vendor[/\\]", re.I),
    re.compile(r"[/\\]\.cache[/\\]", re.I),
    re.compile(r"[/\\]__pycache__[/\\]", re.I),
    re.compile(r"\.min\.(js|css)$", re.I),
    re.compile(r"\.(png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot|otf|pdf|zip|gz|tar)$", re.I),
    re.compile(r"\.(pyc|pyo|class|o|a|so|dll|exe|bin)$", re.I),
]

# Path prefix → tier weight
_TIER_1_PATTERNS: List[re.Pattern] = [
    re.compile(r"^(backend|services|routers|models|agents|core)[/\\]", re.I),
    re.compile(r"^frontend[/\\]src[/\\]", re.I),
    re.compile(r"^src[/\\]", re.I),
    re.compile(r"\.(py|ts|tsx|js|jsx|java|go|rs|rb|cs|cpp|c)$", re.I),
]

_TIER_2_PATTERNS: List[re.Pattern] = [
    re.compile(r"(readme|README)\.", re.I),
    re.compile(r"^docs?[/\\]", re.I),
    re.compile(r"\.(md|rst|txt)$", re.I),
]

_TIER_3_PATTERNS: List[re.Pattern] = [
    re.compile(r"requirements.*\.txt$", re.I),
    re.compile(r"pyproject\.toml$", re.I),
    re.compile(r"setup\.(py|cfg)$", re.I),
    re.compile(r"package\.json$", re.I),
    re.compile(r"tsconfig.*\.json$", re.I),
    re.compile(r"\.(toml|cfg|ini|env\.example)$", re.I),
    re.compile(r"dockerfile$", re.I),
    re.compile(r"docker-compose.*\.yml$", re.I),
]


def _get_tier_weight(file_path: str) -> float:
    """Return the tier weight for a given file path (0.0 = exclude)."""
    p = file_path.replace("\\", "/")

    for pat in _EXCLUDED_PATTERNS:
        if pat.search(p):
            return 0.0

    # Tier 3 checked before Tier 2 because some Tier 3 files (requirements.txt)
    # would otherwise match Tier 2's generic .txt pattern.
    for pat in _TIER_3_PATTERNS:
        if pat.search(p):
            return 0.2

    for pat in _TIER_1_PATTERNS:
        if pat.search(p):
            return 1.0

    for pat in _TIER_2_PATTERNS:
        if pat.search(p):
            return 0.6

    # Default to Tier 1 weight for unknown types
    return 1.0


def _content_hash(content: str) -> str:
    """MD5 of stripped content for deduplication."""
    return hashlib.md5(content.strip().encode("utf-8")).hexdigest()


def _token_overlap_score(query: str, content: str) -> float:
    """Approximate reranking score using normalised token overlap.

    Returns a float in [0, 1]. Higher = better match.
    Avoids loading any ML model — pure string ops.
    """
    def tokenise(text: str) -> set:
        # Lower-case, split on non-alphanumeric, remove stop words
        tokens = re.findall(r"[a-zA-Z_]\w*", text.lower())
        stop = {"the", "a", "an", "is", "in", "it", "of", "to", "do",
                "does", "what", "how", "why", "where", "this", "that",
                "are", "for", "be", "was", "or", "and", "on", "at"}
        return {t for t in tokens if t not in stop and len(t) > 1}

    q_tokens = tokenise(query)
    c_tokens = tokenise(content)

    if not q_tokens:
        return 0.0
    if not c_tokens:
        return 0.0

    overlap = len(q_tokens & c_tokens)
    # Normalise by query length — precision-oriented
    return overlap / len(q_tokens)


# ---------------------------------------------------------------------------
# BGE asymmetric query prefix
# ---------------------------------------------------------------------------

_BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

def build_query_text(question: str) -> str:
    """Prepend the BGE asymmetric query prefix for retrieval queries.

    Documents indexed without any prefix (as BGE asymmetric embedding design
    requires). Queries use this prefix to improve retrieval precision.
    """
    return f"{_BGE_QUERY_PREFIX}{question}"


# ---------------------------------------------------------------------------
# Main retrieval pipeline
# ---------------------------------------------------------------------------

def intelligent_retrieve(
    question: str,
    repo_name: str,
    embedding_service,
    chroma_store,
    top_k_initial: int = 15,
    top_k_final: int = 5,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Full retrieval pipeline: embed → search → weight → rerank → dedup → top-k.

    Args:
        question:          User question (pronoun-resolved).
        repo_name:         Repository identifier (owner/repo).
        embedding_service: EmbeddingService instance.
        chroma_store:      ChromaStore instance.
        top_k_initial:     How many candidates to retrieve before reranking.
        top_k_final:       Final number of chunks to return.

    Returns:
        Tuple of (chunks, metrics_dict).
        chunks: List of dicts with keys: content, metadata, distance, score.
        metrics_dict: Observability data for ChatObservability logger.
    """
    t_total = time.perf_counter()
    metrics: Dict[str, Any] = {
        "initial_retrieved": 0,
        "after_exclusion": 0,
        "after_dedup": 0,
        "final_returned": 0,
        "embed_ms": 0.0,
        "search_ms": 0.0,
        "rerank_ms": 0.0,
    }

    # 1. Embed with asymmetric query prefix
    t0 = time.perf_counter()
    query_text = build_query_text(question)
    query_embedding = embedding_service.generate_embedding(query_text)
    metrics["embed_ms"] = (time.perf_counter() - t0) * 1000

    # 2. Retrieve broader candidate set
    t0 = time.perf_counter()
    raw_chunks = chroma_store.search_repository(
        repo_name=repo_name,
        query_embedding=query_embedding,
        limit=top_k_initial,
    )
    metrics["search_ms"] = (time.perf_counter() - t0) * 1000
    metrics["initial_retrieved"] = len(raw_chunks)

    # 3. Exclude lockfiles / generated / binary files
    filtered: List[Dict[str, Any]] = []
    excluded_paths: List[str] = []
    for chunk in raw_chunks:
        file_path = chunk.get("metadata", {}).get("file_path", "")
        weight = _get_tier_weight(file_path)
        if weight > 0.0:
            chunk["_tier_weight"] = weight
            filtered.append(chunk)
        else:
            excluded_paths.append(file_path)
    metrics["after_exclusion"] = len(filtered)
    if excluded_paths:
        logger.debug(
            "Retrieval: excluded %d lockfile/generated chunks: %s",
            len(excluded_paths), excluded_paths[:3],
        )

    # 4. Deduplicate by content hash
    seen_hashes: set = set()
    deduped: List[Dict[str, Any]] = []
    for chunk in filtered:
        content = chunk.get("content", "")
        h = _content_hash(content)
        if h not in seen_hashes:
            seen_hashes.add(h)
            deduped.append(chunk)
    metrics["after_dedup"] = len(deduped)

    # 5. Rerank using tier weight + token overlap
    t0 = time.perf_counter()
    for chunk in deduped:
        content = chunk.get("content", "")
        overlap = _token_overlap_score(question, content)
        tier_w = chunk.get("_tier_weight", 1.0)
        raw_dist = chunk.get("distance", 1.0)

        # Composite score: lower Chroma distance = better similarity
        # We invert distance (L2): similarity ≈ 1 / (1 + dist)
        similarity = 1.0 / (1.0 + raw_dist)
        chunk["_rerank_score"] = (0.5 * similarity + 0.3 * overlap) * tier_w
        chunk["_similarity"] = round(similarity, 4)
        chunk["_token_overlap"] = round(overlap, 4)

    deduped.sort(key=lambda c: c["_rerank_score"], reverse=True)
    metrics["rerank_ms"] = (time.perf_counter() - t0) * 1000

    # 6. Return top-k final
    final = deduped[:top_k_final]
    metrics["final_returned"] = len(final)
    metrics["total_ms"] = (time.perf_counter() - t_total) * 1000

    logger.info(
        "Retrieval: initial=%d excluded=%d deduped=%d final=%d "
        "embed=%.1fms search=%.1fms rerank=%.1fms",
        metrics["initial_retrieved"],
        metrics["initial_retrieved"] - metrics["after_exclusion"],
        metrics["after_exclusion"] - metrics["after_dedup"],
        metrics["final_returned"],
        metrics["embed_ms"],
        metrics["search_ms"],
        metrics["rerank_ms"],
    )

    return final, metrics


def should_skip_indexing(file_path: str) -> bool:
    """Return True if a file should never be embedded/indexed.

    Called during repository indexing to prevent lockfiles and generated
    code from polluting the vector store.
    """
    return _get_tier_weight(file_path) == 0.0
