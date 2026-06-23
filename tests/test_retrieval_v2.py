"""Repository Chat v2 — comprehensive test suite (Phase 14).

Tests cover:
  - Intent detection (all 9 intents)
  - Intent routing (structured intelligence dispatch)
  - Lockfile exclusion (tier weights)
  - Asymmetric BGE query prefix
  - Reranking and deduplication
  - Conversation memory (pronoun resolution, session TTL)
  - Provider manager (circuit breaker, fallback, streaming retry safety)
  - Fallback rendering (no raw code dumps)
  - Observability (structured trace emission)
  - RetrievalPipeline end-to-end (mocked services)
  - Backward compatibility (RetrievalService shim)
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import AsyncIterator, List


# ---------------------------------------------------------------------------
# Intent Detection
# ---------------------------------------------------------------------------
from services.chat.intent_detector import RuleBasedIntentDetector, Intent


class TestIntentDetector:
    def setup_method(self):
        self.detector = RuleBasedIntentDetector()

    def test_architecture_intent(self):
        r = self.detector.detect("Give me an architecture overview of this codebase")
        assert r.intent == Intent.ARCHITECTURE
        assert r.confidence >= 0.8

    def test_circular_dependency_intent(self):
        r = self.detector.detect("Are there any circular dependencies?")
        assert r.intent == Intent.CIRCULAR_DEPENDENCY

    def test_api_surface_intent(self):
        r = self.detector.detect("List all API endpoints and exported symbols")
        assert r.intent == Intent.API_SURFACE

    def test_call_graph_intent(self):
        r = self.detector.detect("Who calls the UserService.authenticate method?")
        assert r.intent == Intent.CALL_GRAPH

    def test_symbol_intent(self):
        r = self.detector.detect("Where is UserService defined?")
        assert r.intent == Intent.SYMBOL

    def test_reading_order_intent(self):
        r = self.detector.detect("What is the recommended reading order for a new developer?")
        assert r.intent == Intent.READING_ORDER

    def test_impact_analysis_intent(self):
        r = self.detector.detect("What is the blast radius if I change the AuthService?")
        assert r.intent == Intent.IMPACT_ANALYSIS

    def test_general_qa_intent(self):
        r = self.detector.detect("How does the caching layer work?")
        assert r.intent == Intent.GENERAL_QA

    def test_unknown_intent_empty(self):
        r = self.detector.detect("")
        assert r.intent == Intent.UNKNOWN
        assert r.confidence == 0.0

    def test_entity_extraction(self):
        r = self.detector.detect("Explain how UserService and AuthManager work together")
        assert "UserService" in r.entities or "AuthManager" in r.entities

    def test_unknown_intent_random(self):
        r = self.detector.detect("hello there")
        # Should not crash and should return a valid intent
        assert r.intent in list(Intent)


# ---------------------------------------------------------------------------
# Lockfile / Tier Weight Exclusion
# ---------------------------------------------------------------------------
from services.chat.retrieval import _get_tier_weight, should_skip_indexing


class TestTierWeights:
    def test_lockfile_excluded(self):
        assert _get_tier_weight("package-lock.json") == 0.0
        assert _get_tier_weight("pnpm-lock.yaml") == 0.0
        assert _get_tier_weight("yarn.lock") == 0.0
        assert _get_tier_weight("poetry.lock") == 0.0
        assert _get_tier_weight("Cargo.lock") == 0.0

    def test_node_modules_excluded(self):
        assert _get_tier_weight("node_modules/lodash/index.js") == 0.0

    def test_dist_excluded(self):
        assert _get_tier_weight("frontend/dist/bundle.js") == 0.0

    def test_binary_excluded(self):
        assert _get_tier_weight("assets/logo.png") == 0.0
        assert _get_tier_weight("lib/native.so") == 0.0

    def test_tier1_source_code(self):
        assert _get_tier_weight("backend/services/auth.py") == 1.0
        assert _get_tier_weight("services/user_service.py") == 1.0
        assert _get_tier_weight("frontend/src/components/App.tsx") == 1.0

    def test_tier2_docs(self):
        assert _get_tier_weight("README.md") == 0.6
        assert _get_tier_weight("docs/architecture.md") == 0.6

    def test_tier3_config(self):
        assert _get_tier_weight("requirements.txt") == 0.2
        assert _get_tier_weight("pyproject.toml") == 0.2
        assert _get_tier_weight("package.json") == 0.2

    def test_should_skip_indexing(self):
        assert should_skip_indexing("package-lock.json") is True
        assert should_skip_indexing("backend/api.py") is False


# ---------------------------------------------------------------------------
# Asymmetric BGE Query Prefix
# ---------------------------------------------------------------------------
from services.chat.retrieval import build_query_text, _BGE_QUERY_PREFIX


class TestAsymmetricEmbeddings:
    def test_query_prefix_applied(self):
        q = "How does caching work?"
        result = build_query_text(q)
        assert result.startswith(_BGE_QUERY_PREFIX)
        assert q in result

    def test_query_prefix_not_double_applied(self):
        q = "How does caching work?"
        result = build_query_text(q)
        # Should not double-prefix
        assert result.count(_BGE_QUERY_PREFIX) == 1


# ---------------------------------------------------------------------------
# Reranking and Deduplication
# ---------------------------------------------------------------------------
from services.chat.retrieval import _token_overlap_score, _content_hash


class TestReranking:
    def test_token_overlap_exact_match(self):
        score = _token_overlap_score("UserService authentication", "UserService handles authentication")
        assert score > 0.5

    def test_token_overlap_no_match(self):
        score = _token_overlap_score("UserService", "def calculate_tax(): pass")
        assert score < 0.3

    def test_token_overlap_empty_query(self):
        score = _token_overlap_score("", "some content")
        assert score == 0.0

    def test_content_hash_identical(self):
        h1 = _content_hash("def foo(): pass")
        h2 = _content_hash("def foo(): pass")
        assert h1 == h2

    def test_content_hash_different(self):
        h1 = _content_hash("def foo(): pass")
        h2 = _content_hash("def bar(): pass")
        assert h1 != h2

    def test_content_hash_whitespace_normalised(self):
        h1 = _content_hash("  def foo(): pass  ")
        h2 = _content_hash("def foo(): pass")
        assert h1 == h2


# ---------------------------------------------------------------------------
# Conversation Memory
# ---------------------------------------------------------------------------
from services.chat.conversation_memory import ConversationMemoryStore, ConversationSession


class TestConversationMemory:
    def setup_method(self):
        self.store = ConversationMemoryStore()

    def test_create_session(self):
        session = self.store.get_or_create("owner/repo", "s1")
        assert session.repo_name == "owner/repo"
        assert session.session_id == "s1"

    def test_same_session_returned(self):
        s1 = self.store.get_or_create("owner/repo", "s1")
        s2 = self.store.get_or_create("owner/repo", "s1")
        assert s1 is s2

    def test_different_sessions_isolated(self):
        s1 = self.store.get_or_create("owner/repo", "s1")
        s2 = self.store.get_or_create("owner/repo", "s2")
        assert s1 is not s2

    def test_pronoun_resolution_it(self):
        session = self.store.get_or_create("owner/repo", "pronoun_test")
        session.update_context(entities=["UserService"], files=[], intent="SYMBOL")
        resolved = session.resolve_pronouns("What calls it?")
        assert "UserService" in resolved

    def test_pronoun_no_entity_no_crash(self):
        session = self.store.get_or_create("owner/repo", "no_entity")
        result = session.resolve_pronouns("What calls it?")
        # Should return question unchanged without crashing
        assert isinstance(result, str)

    def test_add_turn_bounded(self):
        session = self.store.get_or_create("owner/repo", "bounded")
        for i in range(25):
            session.add_turn("user", f"question {i}")
        assert len(session.turns) <= 20

    def test_clear_session(self):
        self.store.get_or_create("owner/repo", "to_clear")
        self.store.clear_session("owner/repo", "to_clear")
        # New session should be created (not the same object)
        s = self.store.get_or_create("owner/repo", "to_clear")
        assert len(s.turns) == 0

    def test_entity_tracking_deduplication(self):
        session = self.store.get_or_create("owner/repo", "entity_dedup")
        session.update_context(["UserService", "AuthManager"], [], "SYMBOL")
        session.update_context(["UserService"], [], "SYMBOL")
        assert session.last_entities.count("UserService") == 1


# ---------------------------------------------------------------------------
# Provider Manager — circuit breaker and streaming retry safety
# ---------------------------------------------------------------------------
from services.chat.provider_manager import ProviderManager, ProviderEntry, CircuitBreaker, CircuitState


class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_not_allowed_when_open(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        cb.record_failure()
        assert not cb.is_allowed()

    def test_reset_clears_state(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        cb.record_failure()
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.is_allowed()

    def test_success_closes_circuit(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        cb.record_failure()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED


class TestProviderManagerStreaming:
    """Tests for Phase 9 streaming retry safety."""

    def _make_provider(self, tokens=None, fail_after=0):
        """Create a mock provider that streams tokens or fails."""
        provider = MagicMock()

        async def fake_stream(*args, **kwargs) -> AsyncIterator[str]:
            if tokens:
                for i, t in enumerate(tokens):
                    if fail_after > 0 and i >= fail_after:
                        raise RuntimeError("mid-stream failure")
                    yield t
            else:
                raise RuntimeError("provider unavailable")

        provider.stream = fake_stream
        return provider

    def test_stream_yields_tokens(self):
        p = self._make_provider(tokens=["hello", " ", "world"])
        entry = ProviderEntry(name="test", provider=p, priority=1)
        manager = ProviderManager(providers=[entry])

        async def collect():
            results = []
            async for token, pname in manager.stream("prompt"):
                results.append(token)
            return results

        tokens = asyncio.run(collect())
        assert tokens == ["hello", " ", "world"]

    def test_stream_does_not_retry_after_tokens_yielded(self):
        """Phase 9: mid-stream failure must NOT cause duplicate output."""
        p1 = self._make_provider(tokens=["hello", " "], fail_after=2)
        p2 = self._make_provider(tokens=["DUPLICATE"])
        e1 = ProviderEntry(name="p1", provider=p1, priority=1)
        e2 = ProviderEntry(name="p2", provider=p2, priority=2)
        manager = ProviderManager(providers=[e1, e2])

        async def collect():
            results = []
            async for token, pname in manager.stream("prompt"):
                results.append(token)
            return results

        tokens = asyncio.run(collect())
        # p2 tokens must NOT appear — no retry after mid-stream
        assert "DUPLICATE" not in tokens

    def test_stream_retries_on_zero_token_failure(self):
        """If 0 tokens yielded, retry with next provider."""
        p1 = self._make_provider(tokens=None)    # fails immediately
        p2 = self._make_provider(tokens=["ok"])
        e1 = ProviderEntry(name="p1", provider=p1, priority=1)
        e2 = ProviderEntry(name="p2", provider=p2, priority=2)
        manager = ProviderManager(providers=[e1, e2])

        async def collect():
            results = []
            async for token, pname in manager.stream("prompt"):
                results.append(token)
            return results

        tokens = asyncio.run(collect())
        assert "ok" in tokens


# ---------------------------------------------------------------------------
# Fallback Rendering — no raw code dumps
# ---------------------------------------------------------------------------
from services.chat.fallback_renderer import render_fallback, render_mid_stream_termination


class TestFallbackRenderer:
    def test_fallback_no_raw_code_dump(self):
        chunks = [
            {
                "content": "x" * 2000,   # large chunk
                "metadata": {"file_path": "backend/service.py"},
            }
        ]
        result = render_fallback("How does it work?", "", chunks, ["backend/service.py"])
        # Must NOT dump 2000 chars of raw code
        assert "x" * 100 not in result

    def test_fallback_shows_relevant_files(self):
        chunks = [{"content": "def foo(): pass", "metadata": {"file_path": "services/auth.py"}}]
        result = render_fallback("explain auth", "", chunks, ["services/auth.py"])
        assert "services/auth.py" in result

    def test_fallback_shows_structured_intelligence(self):
        intelligence = "## Circular Dependencies\n✅ No cycles detected."
        result = render_fallback("any cycles?", intelligence, [], [])
        assert "Circular Dependencies" in result

    def test_fallback_no_provider_name_exposed(self):
        result = render_fallback("question", "", [], [])
        assert "deepseek" not in result.lower()
        assert "gemini" not in result.lower()
        assert "nvidia" not in result.lower()

    def test_mid_stream_termination_message(self):
        msg = render_mid_stream_termination(tokens_yielded=10)
        assert "incomplete" in msg.lower() or "unavailable" in msg.lower()


# ---------------------------------------------------------------------------
# Observability — trace emission
# ---------------------------------------------------------------------------
from services.chat.observability import ChatObservability, PipelineTrace


class TestObservability:
    def test_emit_does_not_raise(self):
        obs = ChatObservability()
        trace = PipelineTrace(repo_name="owner/repo", session_id="test")
        trace.intent = "GENERAL_QA"
        trace.provider_used = "gemini"
        trace.finish()
        # Should log without exception
        obs.emit(trace)

    def test_trace_finish_sets_total_ms(self):
        import time
        trace = PipelineTrace(repo_name="owner/repo")
        time.sleep(0.01)
        trace.finish()
        assert trace.total_ms >= 5.0   # at least 5ms

    def test_trace_from_retrieval_metrics(self):
        trace = PipelineTrace(repo_name="owner/repo")
        metrics = {
            "initial_retrieved": 15,
            "after_exclusion": 12,
            "after_dedup": 10,
            "final_returned": 5,
            "embed_ms": 42.0,
            "search_ms": 80.0,
            "rerank_ms": 3.0,
        }
        trace.from_retrieval_metrics(metrics)
        assert trace.initial_retrieved == 15
        assert trace.final_returned == 5
        assert trace.embed_ms == 42.0


# ---------------------------------------------------------------------------
# Context Builder
# ---------------------------------------------------------------------------
from services.chat.context_builder import ContextBuilder


class TestContextBuilder:
    def setup_method(self):
        self.builder = ContextBuilder()

    def test_basic_build(self):
        ctx = self.builder.build(
            repo_name="owner/repo",
            question="How does caching work?",
        )
        assert "owner/repo" in ctx.system_instruction
        assert "How does caching work?" in ctx.prompt
        assert ctx.estimated_tokens > 0

    def test_structured_intelligence_included(self):
        ctx = self.builder.build(
            repo_name="owner/repo",
            question="any cycles?",
            structured_intelligence="## Circular Dependencies\n✅ No cycles.",
        )
        assert "Circular Dependencies" in ctx.prompt

    def test_token_budget_enforced(self):
        # Feed oversized content to test budget trimming
        big_chunk = {
            "content": "x" * 30_000,
            "metadata": {"file_path": "backend/big.py"},
        }
        ctx = self.builder.build(
            repo_name="owner/repo",
            question="test",
            code_chunks=[big_chunk],
        )
        # Should not exceed budget by more than a small margin
        assert ctx.estimated_tokens <= 5500

    def test_lockfile_chunks_excluded_from_code_slot(self):
        chunks = [
            {"content": "locked content", "metadata": {"file_path": "package-lock.json"}},
            {"content": "real code", "metadata": {"file_path": "backend/api.py"}},
        ]
        ctx = self.builder.build(
            repo_name="owner/repo",
            question="test",
            code_chunks=chunks,
        )
        # Lockfile content should be excluded from code slot
        assert "locked content" not in ctx.prompt

    def test_source_files_collected(self):
        chunks = [
            {"content": "code", "metadata": {"file_path": "services/auth.py"}},
            {"content": "code2", "metadata": {"file_path": "models/user.py"}},
        ]
        ctx = self.builder.build("owner/repo", "test", code_chunks=chunks)
        assert "services/auth.py" in ctx.source_files
        assert "models/user.py" in ctx.source_files


# ---------------------------------------------------------------------------
# RetrievalPipeline end-to-end (mocked services)
# ---------------------------------------------------------------------------
from services.chat.retrieval_pipeline import RetrievalPipeline
from services.chat.conversation_memory import ConversationMemoryStore


def _make_mock_embedding_service():
    svc = MagicMock()
    svc.generate_embedding.return_value = [0.1] * 384
    return svc


def _make_mock_chroma(chunks=None):
    store = MagicMock()
    store.search_repository.return_value = chunks or [
        {
            "content": "def authenticate(user): pass",
            "metadata": {"file_path": "services/auth.py", "chunk_id": 0},
            "distance": 0.2,
        }
    ]
    return store


def _make_mock_provider(response="This is the answer."):
    provider = MagicMock()

    async def fake_generate(*a, **kw):
        return response, "mock_provider"

    async def fake_stream(*a, **kw) -> AsyncIterator:
        for word in response.split():
            yield word + " ", "mock_provider"

    provider.generate = AsyncMock(return_value=(response, "mock_provider"))
    provider.stream = fake_stream
    return provider


class TestRetrievalPipelineE2E:
    def _make_pipeline(self, provider_response="The answer is here."):
        from services.chat.provider_manager import ProviderManager, ProviderEntry
        emb = _make_mock_embedding_service()
        chroma = _make_mock_chroma()
        provider = _make_mock_provider(provider_response)
        entry = ProviderEntry(name="mock", provider=provider, priority=1)
        pm = ProviderManager(providers=[entry])
        memory = ConversationMemoryStore()
        return RetrievalPipeline(
            embedding_service=emb,
            chroma_store=chroma,
            provider_manager=pm,
            memory_store=memory,
        )

    def test_retrieve_returns_answer(self):
        pipeline = self._make_pipeline("This is the auth service.")
        result = asyncio.run(
            pipeline.retrieve("owner/repo", "How does auth work?")
        )
        assert "answer" in result
        assert len(result["answer"]) > 0

    def test_retrieve_returns_sources(self):
        pipeline = self._make_pipeline()
        result = asyncio.run(
            pipeline.retrieve("owner/repo", "How does auth work?")
        )
        assert "sources" in result
        assert isinstance(result["sources"], list)

    def test_retrieve_stream_yields_sse(self):
        pipeline = self._make_pipeline("Hello world")

        async def collect():
            events = []
            async for sse in pipeline.retrieve_stream("owner/repo", "test question"):
                events.append(sse)
            return events

        events = asyncio.run(collect())
        # All events must be valid SSE format
        for e in events:
            assert e.startswith("data: ")
            data = json.loads(e[6:].strip())
            assert isinstance(data, dict)

    def test_retrieve_stream_done_event(self):
        pipeline = self._make_pipeline("some answer")

        async def collect():
            events = []
            async for sse in pipeline.retrieve_stream("owner/repo", "test"):
                events.append(json.loads(sse[6:].strip()))
            return events

        events = asyncio.run(collect())
        done_events = [e for e in events if e.get("status") == "done"]
        assert len(done_events) == 1
        done = done_events[0]
        assert "sources" in done
        assert "confidence" in done
        assert "fallback_mode" in done

    def test_retrieve_includes_intent(self):
        pipeline = self._make_pipeline()
        result = asyncio.run(
            pipeline.retrieve("owner/repo", "Are there circular dependencies?")
        )
        assert "intent" in result
        assert result["intent"] == "CIRCULAR_DEPENDENCY"


# ---------------------------------------------------------------------------
# Backward compatibility — RetrievalService shim
# ---------------------------------------------------------------------------
from services.retrieval_service import RetrievalService


class TestRetrievalServiceShim:
    """Verify the shim preserves the v1 public API exactly."""

    def test_instantiation_unchanged(self):
        emb = _make_mock_embedding_service()
        store = _make_mock_chroma()
        svc = RetrievalService(embedding_service=emb, chroma_store=store)
        assert svc is not None

    def test_retrieve_and_answer_returns_dict(self):
        emb = _make_mock_embedding_service()
        store = _make_mock_chroma()

        # Patch the pipeline's provider manager so it doesn't call real LLM
        with patch("services.chat.retrieval_pipeline.ProviderManager") as MockPM:
            instance = MockPM.return_value
            instance.generate = AsyncMock(return_value=("test answer", "mock"))
            svc = RetrievalService(embedding_service=emb, chroma_store=store)
            svc._pipeline = None  # force rebuild with mock
            # Patch at pipeline level
            with patch.object(svc, "_get_pipeline") as mock_get:
                mock_pipeline = MagicMock()
                mock_pipeline.retrieve = AsyncMock(return_value={
                    "answer": "test answer",
                    "sources": ["services/auth.py"],
                    "confidence": 85,
                    "verified": True,
                    "evaluation": {},
                    "intent": "GENERAL_QA",
                    "fallback_mode": False,
                })
                mock_get.return_value = mock_pipeline
                result = svc.retrieve_and_answer("owner/repo", "test question")

        assert "answer" in result
        assert "sources" in result
        assert "confidence" in result
        assert "verified" in result
        assert "evaluation" in result


# ---------------------------------------------------------------------------
# Intent Router — basic dispatch
# ---------------------------------------------------------------------------
from services.chat.intent_router import IntentRouter
from services.chat.intent_detector import IntentResult, Intent


class TestIntentRouter:
    def test_unknown_intent_returns_empty(self):
        router = IntentRouter()
        ir = IntentResult(intent=Intent.UNKNOWN)
        result = router.route("owner/repo", "some question", ir)
        assert not result.has_data

    def test_general_qa_returns_empty(self):
        router = IntentRouter()
        ir = IntentResult(intent=Intent.GENERAL_QA)
        result = router.route("owner/repo", "how does it work", ir)
        assert not result.has_data

    def test_architecture_with_no_service_returns_empty(self):
        router = IntentRouter(architecture_service=None)
        ir = IntentResult(intent=Intent.ARCHITECTURE)
        result = router.route("owner/repo", "architecture overview", ir)
        assert not result.has_data

    def test_architecture_with_summary(self):
        mock_arch = MagicMock()
        mock_summary = MagicMock()
        mock_summary.total_files = 42
        mock_summary.total_dependencies = 18
        mock_summary.entry_points = ["backend/main.py"]
        mock_summary.core_modules = ["services/"]
        mock_summary.high_coupling_modules = []
        mock_arch.get_summary.return_value = mock_summary

        router = IntentRouter(architecture_service=mock_arch)
        ir = IntentResult(intent=Intent.ARCHITECTURE)
        result = router.route("owner/repo", "architecture overview", ir)
        assert result.has_data
        assert "42" in result.structured_context

    def test_router_elapsed_ms_set(self):
        router = IntentRouter()
        ir = IntentResult(intent=Intent.UNKNOWN)
        result = router.route("owner/repo", "test", ir)
        assert result.router_elapsed_ms >= 0
