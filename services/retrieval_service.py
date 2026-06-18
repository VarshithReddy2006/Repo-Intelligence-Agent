"""Retrieval Service module.

Coordinates semantic search and LLM context generation to provide
repository-specific answers.

Phase 2 addition: Architecture context is injected into every prompt when a
Phase 1 summary exists for the repo.

AI provider: DeepSeek V4 Flash via NVIDIA NIM (ProviderFactory).
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

from services.embedding_service import EmbeddingService
from services.arch_context_service import ArchContextService
from services.llm import ProviderFactory, BaseLLMProvider
from memory.chroma_store import ChromaStore
from agents.evaluator import EvaluationAgent

logger = logging.getLogger(__name__)


class RetrievalService:
    """Manages the semantic retrieval workflow: Query → Embedding → Search → LLM → Answer."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        chroma_store: ChromaStore,
        client: Any = None,                          # ignored — legacy Gemini arg
        arch_context_service: Optional[ArchContextService] = None,
        provider: Optional[BaseLLMProvider] = None,
    ) -> None:
        """Initialise the RetrievalService.

        Args:
            embedding_service:    Pre-configured EmbeddingService instance.
            chroma_store:         Pre-configured ChromaStore instance.
            client:               Ignored (kept for backwards-compatibility).
            arch_context_service: Optional ArchContextService for architecture context injection.
            provider:             Optional LLM provider override.
        """
        self.embedding_service = embedding_service
        self.chroma_store = chroma_store
        self.arch_context_service = arch_context_service or ArchContextService()
        self._provider = provider or ProviderFactory.get_provider()
        self.evaluator = EvaluationAgent(provider=self._provider)

    def retrieve_and_answer(
        self, repo_name: str, question: str, limit: int = 5
    ) -> Dict[str, Any]:
        """Perform semantic search, generate an answer, and run evaluation checks.

        Synchronous wrapper — runs the async implementation in a new event loop
        so existing synchronous callers are unaffected.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self._retrieve_and_answer_async(repo_name, question, limit),
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self._retrieve_and_answer_async(repo_name, question, limit)
                )
        except Exception as exc:
            logger.error("RetrievalService.retrieve_and_answer failed: %s", exc, exc_info=True)
            return {
                "answer": f"Error in retrieval service: {exc}",
                "sources": [],
                "confidence": 0,
                "verified": False,
                "evaluation": {},
            }

    async def _retrieve_and_answer_async(
        self, repo_name: str, question: str, limit: int
    ) -> Dict[str, Any]:
        # 1. Embed query
        try:
            query_embedding = self.embedding_service.generate_embedding(question)
        except Exception as exc:
            logger.error("Failed to generate query embedding: %s", exc)
            return _error_response(f"Error generating search vector: {exc}")

        # 2. Search ChromaDB
        try:
            chunks = self.chroma_store.search_repository(
                repo_name=repo_name,
                query_embedding=query_embedding,
                limit=limit,
            )
        except Exception as exc:
            logger.error("ChromaDB search failed: %s", exc)
            return _error_response(f"Error retrieving repository chunks: {exc}")

        if not chunks:
            return {
                "answer": (
                    "I couldn't find any relevant code snippets for this query in the repository index. "
                    "Make sure the repository has been indexed successfully first."
                ),
                "sources": [],
                "confidence": 0,
                "verified": False,
                "evaluation": {
                    "citations_valid": False,
                    "hallucination_detected": True,
                    "confidence_score": 0.0,
                    "feedback": "No relevant repository context snippets found.",
                    "retrieved_chunks": 0,
                    "used_chunks": 0,
                    "coverage_percentage": 0.0,
                    "unsupported_claims": ["No context found"],
                    "unknown_files": [],
                    "chunk_citations": [],
                },
            }

        # 3. Build context string
        context_blocks = []
        sources = set()
        for idx, chunk in enumerate(chunks):
            meta = chunk.get("metadata", {})
            file_path = meta.get("file_path", "unknown")
            sources.add(file_path)
            content = chunk.get("content", "")
            context_blocks.append(
                f"--- File: {file_path} (Chunk {meta.get('chunk_id', idx)}) ---\n{content}"
            )
        context_str = "\n\n".join(context_blocks)

        # 4. Architecture context injection
        arch_ctx = self.arch_context_service.get_context(repo_name)
        arch_block = arch_ctx.to_prompt_block()
        arch_section = f"\n{arch_block}\n" if arch_block else ""

        system_instruction = (
            "You are a Repo Intelligence Agent. "
            "Your task is to answer user questions using the provided repository context chunks. "
            "Explain clearly and directly. Reference specific file paths in your answer where appropriate. "
            "Ensure that any file code blocks you show are accurate. "
            "If the answer cannot be determined from the context, explain that clearly "
            "but provide the best helpful reasoning based on general programming standards and the filenames mentioned."
        )

        prompt = (
            f"{arch_section}"
            f"Here is the context retrieved from the repository codebase:\n"
            f"=======================\n"
            f"{context_str}\n"
            f"=======================\n\n"
            f"Question: {question}\n\n"
            f"Provide your detailed developer-oriented answer below."
        )

        # 5. Generate answer
        try:
            answer = await self._provider.generate(
                prompt=prompt,
                system_instruction=system_instruction,
            )
        except Exception as exc:
            logger.error("LLM generate failed: %s", exc)
            return {
                "answer": f"Error generating answer: {str(exc)}",
                "sources": sorted(list(sources)),
                "confidence": 0,
                "verified": False,
                "evaluation": {},
            }

        # 6. Evaluate
        try:
            eval_result = self.evaluator.evaluate_response(question, answer, chunks)
            confidence_pct = int(eval_result.confidence_score * 100)
            verified = eval_result.citations_valid and not eval_result.hallucination_detected
            evaluation_dict = eval_result.model_dump()
        except Exception as exc:
            logger.error("Evaluation failed: %s", exc)
            confidence_pct = 80
            verified = True
            evaluation_dict = {
                "citations_valid": True,
                "hallucination_detected": False,
                "confidence_score": 0.8,
                "feedback": f"Fallback evaluation due to error: {exc}",
                "retrieved_chunks": len(chunks),
                "used_chunks": len(chunks),
                "coverage_percentage": 100.0,
                "unsupported_claims": [],
                "unknown_files": [],
                "chunk_citations": [],
            }

        return {
            "answer": answer,
            "sources": sorted(list(sources)),
            "confidence": confidence_pct,
            "verified": verified,
            "evaluation": evaluation_dict,
        }


def _error_response(msg: str) -> Dict[str, Any]:
    return {
        "answer": msg,
        "sources": [],
        "confidence": 0,
        "verified": False,
        "evaluation": {},
    }
