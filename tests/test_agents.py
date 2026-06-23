"""Unit tests verifying import and initialization interface for agent classes."""

import pytest
from agents import RepositoryAnalyzer, ArchitectureExplainer, IssueMapper, EvaluationAgent


def test_repository_analyzer_init() -> None:
    """Verifies RepositoryAnalyzer can be instantiated and exposes skeleton methods."""
    analyzer = RepositoryAnalyzer()
    assert analyzer is not None
    
    with pytest.raises(NotImplementedError):
        analyzer.analyze_repository("dummy_path")

    with pytest.raises(NotImplementedError):
        analyzer.detect_dependencies([])

    with pytest.raises(NotImplementedError):
        analyzer.detect_tech_stack([])


def test_architecture_explainer_init() -> None:
    """Verifies ArchitectureExplainer can be instantiated and exposes skeleton methods."""
    explainer = ArchitectureExplainer()
    assert explainer is not None

    with pytest.raises(NotImplementedError):
        explainer.recommend_reading_order(None)  # type: ignore

    with pytest.raises(NotImplementedError):
        explainer.explain_component_relationships([])


def test_issue_mapper_init() -> None:
    """Verifies IssueMapper can be instantiated and exposes implemented methods."""
    mapper = IssueMapper()
    assert mapper is not None
    assert hasattr(mapper, "parse_issue")
    assert hasattr(mapper, "identify_relevant_files")
    assert hasattr(mapper, "map_issue")


import json

class MockLLMProvider:
    def __init__(self, should_fail=False, response_json=None):
        self.should_fail = should_fail
        self.response_json = response_json or {
            "citations_valid": True,
            "hallucination_detected": False,
            "confidence_score": 0.95,
            "feedback": "Mock evaluation successful",
            "unsupported_claims": [],
            "unknown_files": [],
            "used_chunks_indices": [0],
            "chunk_citations": [
                {"file_path": "test.py", "chunk_id": "0", "reason": "found match"}
            ]
        }

    async def generate(self, prompt, system_instruction=None, response_mime_type=None):
        if self.should_fail:
            raise RuntimeError("mock provider failure")
        return json.dumps(self.response_json)

    async def stream(self, prompt, system_instruction=None):
        pass


def test_evaluation_agent_init() -> None:
    """Verifies EvaluationAgent can be instantiated and evaluates responses with a mock provider."""
    mock_provider = MockLLMProvider()
    evaluator = EvaluationAgent(provider=mock_provider)
    assert evaluator is not None

    res = evaluator.evaluate_response("What is X?", "X is 10.", ["X is 10 in config."])
    from models.schemas import EvaluationResult
    assert isinstance(res, EvaluationResult)
    assert res.confidence_score == 0.95
    assert res.retrieved_chunks == 1
    assert res.citations_valid is True
    assert res.hallucination_detected is False


def test_evaluation_fallback_when_provider_fails() -> None:
    """If provider generation throws an error, evaluator must use fallback metrics."""
    mock_provider = MockLLMProvider(should_fail=True)
    evaluator = EvaluationAgent(provider=mock_provider)
    res = evaluator.evaluate_response(
        "Where is GraphQL implemented?",
        "GraphQL is implemented in src/graphql_engine.py",
        ["irrelevant snippet"]
    )
    assert res.citations_valid is False
    assert res.hallucination_detected is True
    assert res.confidence_score == 0.0


def test_evaluation_fallback_when_judge_throws() -> None:
    """If the LLM client or evaluator fails for any reason during evaluation, use safe fallback."""
    evaluator = EvaluationAgent(provider=None)
    evaluator._provider = None  # force provider to be None to trigger attribute error fallback
    res = evaluator.evaluate_response(
        "Any question",
        "Any response",
        [{"metadata": {"file_path": "x.py", "chunk_id": 1}, "content": "code"}],
    )

    assert res.citations_valid is False
    assert res.hallucination_detected is True
    assert res.confidence_score == 0.0
