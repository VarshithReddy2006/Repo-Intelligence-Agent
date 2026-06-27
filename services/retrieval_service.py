"""Retrieval Service module — v2 compatibility shim.

This module preserves backward compatibility for all existing callers
(tests, scripts, api.py imports) while delegating to the new authoritative
RetrievalPipeline under the hood.

The public API is identical to v1:
  RetrievalService(embedding_service, chroma_store, ...).retrieve_and_answer(...)

Internal logic is now in services/chat/retrieval_pipeline.py.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from services.embedding_service import EmbeddingService
from services.arch_context_service import ArchContextService
from services.llm import ProviderFactory, BaseLLMProvider
from memory.chroma_store import ChromaStore
from agents.evaluator import EvaluationAgent

logger = logging.getLogger(__name__)


class RetrievalService:
    """Compatibility shim — delegates to RetrievalPipeline.

    Preserves the existing constructor signature so existing callers
    (tests, scripts, issue_mapper.py) continue to work without changes.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        chroma_store: ChromaStore,
        client: Any = None,
        arch_context_service: Optional[ArchContextService] = None,
        provider: Optional[BaseLLMProvider] = None,
    ) -> None:
        self.embedding_service = embedding_service
        self.chroma_store = chroma_store
        self.arch_context_service = arch_context_service or ArchContextService()
        self._provider = provider or ProviderFactory.get_provider()
        self.evaluator = EvaluationAgent(provider=self._provider)
        # Lazy-built pipeline (avoids circular imports at module load)
        self._pipeline = None

    def _get_pipeline(self):
        """Lazily build a RetrievalPipeline using injected services."""
        if self._pipeline is not None:
            return self._pipeline
        from services.chat.retrieval_pipeline import RetrievalPipeline

        self._pipeline = RetrievalPipeline(
            embedding_service=self.embedding_service,
            chroma_store=self.chroma_store,
            arch_context_service=self.arch_context_service,
        )
        return self._pipeline

    def retrieve_and_answer(
        self, repo_name: str, question: str, limit: int = 5
    ) -> Dict[str, Any]:
        """Perform semantic search and generate an answer.

        Synchronous wrapper — delegates to RetrievalPipeline.retrieve().
        """
        try:
            pipeline = self._get_pipeline()
            try:
                loop = asyncio.get_running_loop()
                is_running = loop.is_running()
            except RuntimeError:
                is_running = False

            if is_running:
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        pipeline.retrieve(repo_name, question),
                    )
                    return future.result()
            else:
                return asyncio.run(pipeline.retrieve(repo_name, question))
        except Exception as exc:
            logger.error(
                "RetrievalService.retrieve_and_answer failed: %s", exc, exc_info=True
            )
            return _error_response(f"Error in retrieval service: {exc}")


def _error_response(msg: str) -> Dict[str, Any]:
    return {
        "answer": msg,
        "sources": [],
        "confidence": 0,
        "verified": False,
        "evaluation": {},
    }
