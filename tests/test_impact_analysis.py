"""Unit tests for ImpactAnalysisService and its corresponding API endpoint."""

import os
import sys
import pytest
from fastapi.testclient import TestClient
import networkx as nx

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api import app
from services.impact_analysis_service import ImpactAnalysisService
from models.architecture import ArchitectureSummary
from models.phase2 import ImpactAnalysis


class DummyGraphService:
    def __init__(self, graph: nx.DiGraph) -> None:
        self.graph = graph

    def load_graph(self, repo_name: str) -> nx.DiGraph:
        if repo_name == "error/repo":
            return None
        return self.graph


class DummyArchitectureService:
    def __init__(self, summary: ArchitectureSummary) -> None:
        self.summary = summary

    def get_summary(self, repo_name: str) -> ArchitectureSummary:
        if repo_name == "error/repo":
            return None
        return self.summary


@pytest.fixture
def sample_graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    # Create nodes
    graph.add_node("backend/main.py")
    graph.add_node("services/api.py")
    graph.add_node("services/auth.py")
    graph.add_node("services/user_service.py")
    graph.add_node("utils/helpers.py")

    # Create dependency edges (caller -> callee / importer -> imported)
    graph.add_edge("backend/main.py", "services/api.py")
    graph.add_edge("services/api.py", "services/auth.py")
    graph.add_edge("services/auth.py", "services/user_service.py")
    graph.add_edge("services/user_service.py", "utils/helpers.py")
    return graph


@pytest.fixture
def sample_summary() -> ArchitectureSummary:
    return ArchitectureSummary(
        entry_points=["backend/main.py"],
        core_modules=["services/auth.py"],
        high_coupling_modules=["services/api.py"],
        total_files=5,
        total_dependencies=4,
    )


def test_keyword_extraction() -> None:
    """Verifies that keywords are extracted correctly from issue text."""
    issue = "Fix memory leaks in cache store"
    kws = ImpactAnalysisService._extract_keywords(issue)
    assert "memory" in kws
    assert "leaks" in kws
    assert "cache" in kws
    assert "store" in kws
    # Stopwords should be filtered out
    assert "in" not in kws


def test_impact_analysis_logic(sample_graph, sample_summary) -> None:
    """Verifies impact analysis correctly traverses forward/backward dependencies and scores risk."""
    graph_svc = DummyGraphService(sample_graph)
    arch_svc = DummyArchitectureService(sample_summary)

    service = ImpactAnalysisService(
        architecture_service=arch_svc, graph_service=graph_svc
    )

    # Target "services/auth.py" by querying oauth/login
    issue = "Implement GitHub OAuth login for users"
    analysis = service.analyze_change("owner/repo", issue)

    assert isinstance(analysis, ImpactAnalysis)
    assert analysis.repo == "owner/repo"
    assert analysis.issue_text == issue

    # "services/auth.py" should be directly affected (matched via keyword "login/oauth" and substring)
    assert "services/auth.py" in analysis.directly_affected_files

    # "services/api.py" imports "services/auth.py", so it should be directly/indirectly affected
    assert (
        "services/api.py" in analysis.directly_affected_files
        or "services/api.py" in analysis.indirectly_affected_files
    )

    # "services/user_service.py" is imported by "services/auth.py", so it should be affected
    assert (
        "services/user_service.py" in analysis.directly_affected_files
        or "services/user_service.py" in analysis.indirectly_affected_files
    )

    # Verification of risk level
    assert analysis.risk_level in ("low", "medium", "high")
    assert analysis.confidence > 0
    assert len(analysis.affected_components) > 0


def test_impact_analysis_missing_graph() -> None:
    """ImpactAnalysisService should raise ValueError if no graph exists."""
    graph_svc = DummyGraphService(nx.DiGraph())  # empty graph
    arch_svc = DummyArchitectureService(ArchitectureSummary())

    service = ImpactAnalysisService(
        architecture_service=arch_svc, graph_service=graph_svc
    )
    with pytest.raises(ValueError):
        service.analyze_change("error/repo", "any issue")


def test_impact_analysis_api_route() -> None:
    """Verifies that POST /api/impact-analysis works or fails gracefully."""
    client = TestClient(app)

    # We test on an unbuilt repository, which should return 404
    response = client.post(
        "/api/impact-analysis",
        json={"repo": "nonexistent/repo-123", "issue": "Add feature X"},
    )
    assert response.status_code == 404
    assert "detail" in response.json()
