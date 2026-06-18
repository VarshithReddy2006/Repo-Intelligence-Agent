"""Unit tests for ReadingOrderService and its corresponding API endpoint."""

import os
import sys
import pytest
from fastapi.testclient import TestClient
import networkx as nx

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api import app
from services.reading_order_service import ReadingOrderService
from models.architecture import ArchitectureSummary
from models.phase2 import ReadingOrder


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
    graph.add_node("services/retrieval_service.py")
    graph.add_node("utils/helpers.py")
    graph.add_node("tests/test_main.py")
    
    # Create dependency edges (caller -> callee / importer -> imported)
    graph.add_edge("backend/main.py", "services/api.py")
    graph.add_edge("services/api.py", "services/retrieval_service.py")
    graph.add_edge("services/retrieval_service.py", "utils/helpers.py")
    graph.add_edge("tests/test_main.py", "backend/main.py")
    return graph


@pytest.fixture
def sample_summary() -> ArchitectureSummary:
    return ArchitectureSummary(
        entry_points=["backend/main.py"],
        core_modules=["services/api.py"],
        high_coupling_modules=[],
        total_files=5,
        total_dependencies=4,
    )


def test_reading_order_calculation(sample_graph, sample_summary) -> None:
    """Verifies ReadingOrderService prioritizes and orders files correctly."""
    graph_svc = DummyGraphService(sample_graph)
    arch_svc = DummyArchitectureService(sample_summary)
    
    service = ReadingOrderService(architecture_service=arch_svc, graph_service=graph_svc)
    reading_order = service.generate_reading_order("owner/repo")
    
    assert isinstance(reading_order, ReadingOrder)
    assert reading_order.repo == "owner/repo"
    assert len(reading_order.ordered_files) == 5
    
    # 1. Entry point (backend/main.py) must be near the top
    first_file = reading_order.ordered_files[0]
    assert first_file.file_path == "backend/main.py"
    assert first_file.tier == "entry_point"
    
    # 2. Core module (services/api.py) should have higher rank than leaf utils
    ordered_paths = [entry.file_path for entry in reading_order.ordered_files]
    api_idx = ordered_paths.index("services/api.py")
    helpers_idx = ordered_paths.index("utils/helpers.py")
    assert api_idx < helpers_idx
    
    # 3. Peripheral/test file (tests/test_main.py) should be pushed toward the end
    test_idx = ordered_paths.index("tests/test_main.py")
    assert test_idx > api_idx
    
    # 4. Reading time estimate is greater than 0
    assert reading_order.estimated_reading_time > 0
    assert len(reading_order.reasoning) > 0


def test_reading_order_missing_graph() -> None:
    """ReadingOrderService should raise ValueError if no graph exists."""
    graph_svc = DummyGraphService(nx.DiGraph())  # empty graph
    arch_svc = DummyArchitectureService(ArchitectureSummary())
    
    service = ReadingOrderService(architecture_service=arch_svc, graph_service=graph_svc)
    with pytest.raises(ValueError):
        service.generate_reading_order("error/repo")


def test_reading_order_api_route() -> None:
    """Verifies that POST /api/reading-order works end-to-end or fails gracefully."""
    client = TestClient(app)
    
    # We test on an unbuilt repository first, which should return 404
    response = client.post("/api/reading-order", json={"repo": "nonexistent/repo-123"})
    assert response.status_code == 404
    assert "detail" in response.json()
