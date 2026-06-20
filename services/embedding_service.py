"""Embedding Service — local BGE embeddings via sentence-transformers.

Replaces Gemini text-embedding-004 with BAAI/bge-small-en-v1.5 running
entirely locally. No API calls, no quotas, no API key required.

Public interface is identical to the previous Gemini-backed version so all
callers (RetrievalService, IssueMapper, ChromaStore, api.py) continue to work
without modification.
"""

import logging
import threading
import time
from typing import List, Union, Dict, Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model singleton — loaded once and reused across all calls
# ---------------------------------------------------------------------------
_model_lock = threading.Lock()
_model = None
_MODEL_NAME = "BAAI/bge-small-en-v1.5"


def _get_model():
    """Return the cached SentenceTransformer model, loading it on first call."""
    global _model
    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:  # double-checked locking
            return _model

        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            logger.info("Loading BGE embedding model '%s' (first call)…", _MODEL_NAME)
            t0 = time.perf_counter()
            _model = SentenceTransformer(_MODEL_NAME)
            logger.info(
                "BGE model loaded successfully. elapsed=%.2fs",
                time.perf_counter() - t0,
            )
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Run: pip install sentence-transformers"
            ) from exc

    return _model


# ---------------------------------------------------------------------------
# Compatibility shim — call_with_retry was imported by other modules from here
# ---------------------------------------------------------------------------

def call_with_retry(func, *args, max_retries: int = 5, initial_delay: float = 1.0,
                    backoff_factor: float = 2.0, **kwargs):
    """Thin compatibility shim — local inference never needs retry, but this
    function is imported by agents/evaluator.py and agents/issue_mapper.py so
    it must remain importable.  For local models it simply calls the function
    directly.
    """
    return func(*args, **kwargs)


# ---------------------------------------------------------------------------
# EmbeddingService
# ---------------------------------------------------------------------------

class EmbeddingService:
    """Generates dense vector embeddings using a local BGE model.

    Drop-in replacement for the previous Gemini-backed EmbeddingService.
    Constructor accepts the same optional `client` and `model_name` kwargs so
    existing call-sites that pass `client=...` do not break.
    """

    def __init__(
        self,
        client: Any = None,          # accepted but ignored (Gemini client)
        model_name: str = _MODEL_NAME,
    ) -> None:
        """Initialise the EmbeddingService.

        Args:
            client:     Ignored.  Accepted for backwards-compatibility only.
            model_name: Name of the sentence-transformers model to load.
                        Defaults to BAAI/bge-small-en-v1.5.
        """
        if client is not None:
            logger.debug(
                "EmbeddingService: 'client' parameter is ignored — using local BGE model."
            )
        self.model_name = model_name
        # ponytail: lazy load — model loads on first generate_embedding(s) call.
        # Eager load duplicated under uvicorn --reload (reloader parent + worker
        # both instantiated EmbeddingService at import time). Singleton in
        # _get_model() still guarantees one load per process.

    # ------------------------------------------------------------------
    # Core embedding methods
    # ------------------------------------------------------------------

    def generate_embedding(self, text: str) -> List[float]:
        """Generate a single embedding vector for the given text.

        Args:
            text: The input string.

        Returns:
            A list of floats representing the embedding vector.
        """
        model = _get_model()
        # BGE models benefit from a query prefix when used for retrieval
        encoded = model.encode(
            f"Represent this sentence: {text}",
            normalize_embeddings=True,
        )
        return encoded.tolist()

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of strings in one efficient batch.

        Args:
            texts: List of input strings.

        Returns:
            A list of embedding vectors.
        """
        if not texts:
            return []

        model = _get_model()
        # Prefix each text for consistency with generate_embedding
        prefixed = [f"Represent this sentence: {t}" for t in texts]
        batch_size = 64
        t0 = time.perf_counter()
        logger.debug("Encoding %d chunks with batch size %d", len(prefixed), batch_size)
        encoded = model.encode(
            prefixed,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        elapsed = time.perf_counter() - t0
        logger.info(
            "BGE encode completed n_texts=%d batch_size=%d elapsed=%.2fs",
            len(prefixed),
            batch_size,
            elapsed,
        )
        return [vec.tolist() for vec in encoded]

    def generate_embeddings(
        self, chunks: List[Union[str, Dict[str, Any], Any]]
    ) -> List[List[float]]:
        """Generate embeddings for a mixed list of chunks, dicts, or strings.

        Accepts the same input formats as the old Gemini-backed version:
        - Plain strings
        - Dicts with a "content" key
        - Objects with a .content attribute

        Args:
            chunks: List of chunk structures or text strings.

        Returns:
            A list of embedding vectors.
        """
        texts: List[str] = []
        for c in chunks:
            if isinstance(c, str):
                texts.append(c)
            elif isinstance(c, dict) and "content" in c:
                texts.append(c["content"])
            elif hasattr(c, "content"):
                texts.append(getattr(c, "content"))
            else:
                texts.append(str(c))

        return self.generate_embeddings_batch(texts)
