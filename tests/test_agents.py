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
    """Verifies IssueMapper can be instantiated and exposes skeleton methods."""
    mapper = IssueMapper()
    assert mapper is not None

    with pytest.raises(NotImplementedError):
        mapper.map_issue("test issue", "fix it")

    with pytest.raises(NotImplementedError):
        mapper.identify_relevant_files("error in cache")

    with pytest.raises(NotImplementedError):
        mapper.generate_plan("error in cache", [])


def test_evaluation_agent_init() -> None:
    """Verifies EvaluationAgent can be instantiated and exposes skeleton methods."""
    evaluator = EvaluationAgent()
    assert evaluator is not None

    with pytest.raises(NotImplementedError):
        evaluator.evaluate_response("prompt", "response", [])
