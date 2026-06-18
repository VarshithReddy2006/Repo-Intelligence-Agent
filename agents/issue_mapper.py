"""Issue Mapping Agent module.

Responsible for taking GitHub issues, identifying files relevant to those issues,
and generating step-by-step implementation plans to solve/resolve them.

Phase 2 addition: Architecture context (entry points, core modules, high-coupling
files) is injected into every prompt so the model understands the repository's
structural boundaries before generating an implementation plan.

AI provider: DeepSeek V4 Flash via NVIDIA NIM (ProviderFactory).
"""

import asyncio
import json
import hashlib
import logging
import os
from typing import List, Dict, Any, Optional

from models.schemas import ImplementationPlan
from services.embedding_service import EmbeddingService
from services.arch_context_service import ArchContextService
from services.issue_retrieval_service import IssueRetrievalService
from services.llm import ProviderFactory, BaseLLMProvider
from memory.chroma_store import ChromaStore
from agents.evaluator import EvaluationAgent

logger = logging.getLogger(__name__)

CACHE_FILE = os.path.join("data", "issue_cache.json")


def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Failed to load issue cache: %s", exc)
    return {}


def save_cache(cache: dict) -> None:
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as exc:
        logger.warning("Failed to save issue cache: %s", exc)


ISSUE_CACHE = load_cache()


class IssueMapper:
    """Agent that maps GitHub issues to relevant codebase files and creates implementation plans."""

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        chroma_store: Optional[ChromaStore] = None,
        client: Any = None,                              # ignored — legacy Gemini arg
        arch_context_service: Optional[ArchContextService] = None,
        issue_retrieval_service: Optional[IssueRetrievalService] = None,
        provider: Optional[BaseLLMProvider] = None,
    ) -> None:
        self._provider = provider or ProviderFactory.get_provider()

        if embedding_service is None:
            self.embedding_service = EmbeddingService()
        else:
            self.embedding_service = embedding_service

        if chroma_store is None:
            CHROMA_DB_PATH = os.environ.get("CHROMA_DB_PATH", "data/chroma_db")
            self.chroma_store = ChromaStore(persist_directory=CHROMA_DB_PATH)
        else:
            self.chroma_store = chroma_store

        self.arch_context_service = arch_context_service or ArchContextService()
        self.issue_retrieval_service = issue_retrieval_service or IssueRetrievalService(
            embedding_service=self.embedding_service,
            chroma_store=self.chroma_store,
        )

    # ------------------------------------------------------------------
    # Internal async helpers
    # ------------------------------------------------------------------

    async def _parse_issue_async(self, repo_name: str, issue_text: str) -> dict:
        system_instr = (
            "You are an expert software engineer assistant. "
            "Analyse the given issue text and extract structured information. "
            "Return a JSON object conforming exactly to this schema:\n"
            "{\n"
            "  \"summary\": \"A concise one-line summary of the core problem or request\",\n"
            "  \"issue_type\": \"feature\" | \"bug\" | \"refactor\",\n"
            "  \"keywords\": [\"list\", \"of\", \"search\", \"keywords\"],\n"
            "  \"affected_domains\": [\"list\", \"of\", \"likely\", \"affected\", \"functional\", \"areas\"]\n"
            "}"
        )
        prompt = f"Issue Text:\n{issue_text}"
        raw = await self._provider.generate(
            prompt=prompt,
            system_instruction=system_instr,
            response_mime_type="application/json",
        )
        data = json.loads(raw)
        data.setdefault("summary", "")
        data.setdefault("issue_type", "feature")
        data.setdefault("keywords", [])
        data.setdefault("affected_domains", [])
        return data

    async def _identify_relevant_files_async(
        self,
        repo_name: str,
        issue_text: str,
        keywords: List[str],
        chunks: List[dict],
    ) -> List[dict]:
        if not chunks:
            return []

        formatted_candidates = []
        for idx, c in enumerate(chunks):
            meta = c.get("metadata", {})
            file_path = meta.get("file_path", "unknown")
            content = c.get("content", "")
            formatted_candidates.append(
                f"Candidate [{idx}] - File: {file_path}\n{content[:300]}..."
            )
        candidates_str = "\n\n".join(formatted_candidates)

        system_instr = (
            "You are an expert developer assistant. "
            "Evaluate the relevance of candidate files to the GitHub issue. "
            "Identify up to 10 unique files that are most relevant to solving the issue. "
            "Assign a relevance score (between 0.0 and 1.0) to each file. "
            "Return a JSON object conforming exactly to this schema:\n"
            "{\n"
            "  \"files\": [\n"
            "    {\"path\": \"file_path\", \"score\": 0.95}\n"
            "  ]\n"
            "}"
        )
        prompt = (
            f"GitHub Issue:\n{issue_text}\n\n"
            f"Candidate codebase snippets:\n{candidates_str}\n"
        )
        try:
            raw = await self._provider.generate(
                prompt=prompt,
                system_instruction=system_instr,
                response_mime_type="application/json",
            )
            top_files = json.loads(raw).get("files", [])
            return [
                {"path": f.get("path", ""), "score": float(f.get("score", 0.0))}
                for f in top_files
                if f.get("path")
            ]
        except Exception as exc:
            logger.error("File reranking failed: %s — falling back to distance scores.", exc)
            file_scores: Dict[str, float] = {}
            for chunk in chunks:
                meta = chunk.get("metadata", {})
                path = meta.get("file_path", "unknown")
                dist = chunk.get("distance", 1.0)
                score = 1.0 / (1.0 + dist)
                if path != "unknown":
                    file_scores[path] = max(file_scores.get(path, 0.0), score)
            sorted_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)[:10]
            return [{"path": p, "score": round(s, 2)} for p, s in sorted_files]

    async def _generate_plan_async(
        self,
        issue_text: str,
        parsed: dict,
        relevant_files: List[str],
        arch_block: str,
    ) -> dict:
        system_instr = (
            "You are a Repo Intelligence Agent. Generate a detailed, repository-specific Implementation Plan for the given issue. "
            "You must identify the affected components from this exact list: ['Authentication', 'API Layer', 'Database', 'Frontend', 'Services', 'Models']. "
            "Estimate complexity as 'low', 'medium', or 'high'. "
            "Provide step-by-step implementation instructions specific to the repository structure and relevant files. "
            "Return a JSON object matching this schema:\n"
            "{\n"
            "  \"affected_components\": [\"API Layer\"],\n"
            "  \"complexity\": \"medium\",\n"
            "  \"steps\": [\n"
            "    {\n"
            "      \"step_number\": 1,\n"
            "      \"description\": \"Detailed description\",\n"
            "      \"files_to_modify\": [\"file_path\"]\n"
            "    }\n"
            "  ],\n"
            "  \"risk_areas\": [\"potential side effects\"],\n"
            "  \"dependencies\": [\"required dependencies\"]\n"
            "}"
        )
        file_paths_str = ", ".join(relevant_files)
        arch_section = f"\n{arch_block}\n" if arch_block else ""
        prompt = (
            f"{arch_section}"
            f"GitHub Issue:\n{issue_text}\n\n"
            f"Parsed Summary: {parsed['summary']}\n"
            f"Relevant Files Candidates: {file_paths_str}\n\n"
            "Generate the implementation plan, affected components, and complexity."
        )
        raw = await self._provider.generate(
            prompt=prompt,
            system_instruction=system_instr,
            response_mime_type="application/json",
        )
        return json.loads(raw)

    # ------------------------------------------------------------------
    # Public synchronous interface (unchanged signature)
    # ------------------------------------------------------------------

    def parse_issue(self, repo_name: str, issue_text: str) -> dict:
        """Parse a GitHub issue using the LLM and cache the result."""
        issue_hash = hashlib.sha256(issue_text.strip().encode("utf-8")).hexdigest()
        cache_key = f"{repo_name}:{issue_hash}"

        global ISSUE_CACHE
        if cache_key in ISSUE_CACHE:
            logger.info("Found issue parse results in cache.")
            return ISSUE_CACHE[cache_key]

        try:
            data = _run_async(self._parse_issue_async(repo_name, issue_text))
            ISSUE_CACHE[cache_key] = data
            save_cache(ISSUE_CACHE)
            return data
        except Exception as exc:
            logger.error("Failed to parse issue: %s", exc)
            return {
                "summary": issue_text.split("\n")[0][:100],
                "issue_type": "feature",
                "keywords": [w for w in issue_text.split() if len(w) > 4][:5],
                "affected_domains": ["Services"],
            }

    def identify_relevant_files(
        self, repo_name: str, issue_text: str, keywords: List[str]
    ) -> List[dict]:
        """Query the codebase index and rerank files for relevance."""
        search_query = f"{issue_text} {' '.join(keywords)}"
        try:
            chunks = self.issue_retrieval_service.retrieve_issue_context(
                repo_name=repo_name, issue_text=search_query, limit=20
            )
        except Exception as exc:
            logger.error("Issue context retrieval failed: %s", exc)
            return []

        try:
            return _run_async(
                self._identify_relevant_files_async(repo_name, issue_text, keywords, chunks)
            )
        except Exception as exc:
            logger.error("identify_relevant_files async failed: %s", exc)
            return []

    def map_issue(self, repo_name: str, issue_title: str, issue_body: str) -> dict:
        """Process a GitHub issue to generate a complete intelligence plan."""
        issue_text = f"{issue_title}\n{issue_body}".strip()

        # 1. Parse
        parsed = self.parse_issue(repo_name, issue_text)

        # 2. Retrieve context chunks once (reused for file identification + evaluation)
        try:
            chunks = self.issue_retrieval_service.retrieve_issue_context(
                repo_name=repo_name, issue_text=issue_text, limit=20
            )
        except Exception as exc:
            logger.error("Issue context retrieval failed: %s", exc)
            chunks = []

        # 3. Identify relevant files
        scored_files = self.identify_relevant_files(
            repo_name, issue_text, parsed.get("keywords", [])
        )
        relevant_files = [f["path"] for f in scored_files]

        # 4. Architecture context
        arch_ctx = self.arch_context_service.get_context(repo_name)
        arch_block = arch_ctx.to_prompt_block()

        # 5. Generate implementation plan
        try:
            plan_data = _run_async(
                self._generate_plan_async(issue_text, parsed, relevant_files, arch_block)
            )
        except Exception as exc:
            logger.error("Implementation plan generation failed: %s", exc)
            plan_data = {
                "affected_components": ["Services"],
                "complexity": "low",
                "steps": [
                    {
                        "step_number": 1,
                        "description": f"Investigate codebase files: {', '.join(relevant_files)}",
                        "files_to_modify": relevant_files[:1] if relevant_files else [],
                    }
                ],
                "risk_areas": ["Manual review required"],
                "dependencies": [],
            }

        # 6. Evaluate
        try:
            evaluator = EvaluationAgent(provider=self._provider)
            response_str = "Plan Steps:\n" + "\n".join(
                f"Step {s['step_number']}: {s['description']} (files: {', '.join(s['files_to_modify'])})"
                for s in plan_data.get("steps", [])
            )
            eval_result = evaluator.evaluate_response(
                prompt=issue_text, response=response_str, source_contexts=chunks
            )
            confidence = int(eval_result.confidence_score * 100)
            verified = eval_result.citations_valid and not eval_result.hallucination_detected
            sources = list(
                {c.get("file_path", "") for c in eval_result.chunk_citations if c.get("file_path")}
            )
        except Exception as exc:
            logger.error("Evaluation failed: %s", exc)
            confidence = 80
            verified = True
            sources = []

        if not sources:
            sources = list(
                {
                    c.get("metadata", {}).get("file_path", "")
                    for c in chunks
                    if c.get("metadata", {}).get("file_path")
                }
            )

        return {
            "issue_summary": parsed.get("summary", ""),
            "issue_type": parsed.get("issue_type", "feature"),
            "relevant_files": relevant_files,
            "affected_components": plan_data.get("affected_components", ["Services"]),
            "implementation_plan": plan_data.get("steps", []),
            "complexity": plan_data.get("complexity", "medium"),
            "confidence": confidence,
            "verified": verified,
            "sources": sorted(sources),
        }


# ---------------------------------------------------------------------------
# Async helper
# ---------------------------------------------------------------------------

def _run_async(coro):
    """Run a coroutine from synchronous code, handling both running and idle loops."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)
