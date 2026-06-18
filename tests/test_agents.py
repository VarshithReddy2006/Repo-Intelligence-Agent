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


def test_evaluation_agent_init() -> None:
    """Verifies EvaluationAgent can be instantiated and evaluates responses."""
    evaluator = EvaluationAgent()
    assert evaluator is not None

    res = evaluator.evaluate_response("What is X?", "X is 10.", ["X is 10 in config."])
    from models.schemas import EvaluationResult
    assert isinstance(res, EvaluationResult)
    assert res.confidence_score >= 0.0
    assert res.retrieved_chunks == 1


def test_evaluation_fallback_when_client_not_initialized() -> None:
    """If Gemini client is not initialized, evaluator must mark citations invalid + hallucination detected."""
    evaluator = EvaluationAgent(client=None)
    res = evaluator.evaluate_response(
        "Where is GraphQL implemented?",
        "GraphQL is implemented in src/graphql_engine.py",
        ["irrelevant snippet"]
    )
    assert res.citations_valid is False
    assert res.hallucination_detected is True
    assert res.confidence_score == 0.0


def test_evaluation_fallback_when_judge_throws() -> None:
    """If judge call fails, evaluator must use the safe fallback (no optimistic validity)."""
    class _DummyModels:
        def generate_content(self, *args, **kwargs):
            raise RuntimeError("judge call failed")

    class _DummyClient:
        models = _DummyModels()

    evaluator = EvaluationAgent(client=_DummyClient())  # client exists -> go to judge -> except -> fallback
    res = evaluator.evaluate_response(
        "Any question",
        "Any response",
        [{"metadata": {"file_path": "x.py", "chunk_id": 1}, "content": "code"}],
    )

    assert res.citations_valid is False
    assert res.hallucination_detected is True
    assert res.confidence_score == 0.0
