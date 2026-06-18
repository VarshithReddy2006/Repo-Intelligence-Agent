"""Unit tests for the Architecture Graph API endpoint."""

import os
import sys
import pytest
from fastapi.testclient import TestClient
import networkx as nx

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api import app
from services.architecture_service import ArchitectureService
from services.graph_service import GraphService


@pytest.fixture(scope="module")
def setup_test_repo():
    """Sets up a synthetic repository, builds its architecture graph, and saves it."""
    arch_service = ArchitectureService()
    repo_name = "testowner/testrepo"
    
    files = [
        {"path": "backend/api.py", "content": "import services.auth_service\nimport services.retrieval_service"},
        {"path": "services/auth_service.py", "content": "import db.models"},
        {"path": "services/retrieval_service.py", "content": "import db.models"},
        {"path": "db/models.py", "content": ""},
        {"path": "tests/test_api.py", "content": "import backend.api"},
        {"path": "docs/index.md", "content": ""},
    ]
    
    # Run the build pipeline to generate persisted summary & graph
    result = arch_service.build(
        repo_name=repo_name,
        files=files,
        force_rebuild=True
    )
    
    yield repo_name, files
    
    # Cleanup persisted files after tests
    summary_path = arch_service._summary_path(repo_name)
    if os.path.exists(summary_path):
        os.remove(summary_path)
        
    graph_path = arch_service.graph_service.graphs_dir
    safe_name = repo_name.replace("/", "_")
    pkl_path = os.path.join(graph_path, f"{safe_name}.pkl")
    if os.path.exists(pkl_path):
        os.remove(pkl_path)


def test_graph_api_returns_nodes_and_edges(setup_test_repo) -> None:
    """Verifies that the graph API endpoint returns a valid React Flow payload."""
    repo_name, _ = setup_test_repo
    client = TestClient(app)
    
    response = client.get(f"/api/architecture/{repo_name}/graph")
    assert response.status_code == 200
    data = response.json()
    
    assert "nodes" in data
    assert "edges" in data
    
    # 1. Verify Node structure
    nodes = data["nodes"]
    assert len(nodes) > 0
    for node in nodes:
        assert "id" in node
        assert "label" in node
        assert "category" in node
        assert "degree" in node
        assert "centrality" in node
        
    # 2. Verify Edge structure
    edges = data["edges"]
    assert len(edges) > 0
    for edge in edges:
        assert "source" in edge
        assert "target" in edge
        assert "relationship" in edge


def test_graph_api_clustering(setup_test_repo) -> None:
    """Verifies that tests/ and docs/ files are collapsed into directory nodes."""
    repo_name, _ = setup_test_repo
    client = TestClient(app)
    
    response = client.get(f"/api/architecture/{repo_name}/graph")
    data = response.json()
    nodes = data["nodes"]
    node_ids = {n["id"] for n in nodes}
    
    # Individual test/doc files should not exist as separate nodes
    assert "tests/test_api.py" not in node_ids
    
    # The collapsed directory nodes should exist
    assert "tests/" in node_ids
    
    # Verify tests/ category is "directory"
    tests_node = next(n for n in nodes if n["id"] == "tests/")
    assert tests_node["category"] == "directory"


def test_graph_api_search_filtering(setup_test_repo) -> None:
    """Verifies search filtering returns matching nodes and immediate neighbors."""
    repo_name, _ = setup_test_repo
    client = TestClient(app)
    
    # Query for "auth"
    response = client.get(f"/api/architecture/{repo_name}/graph?q=auth")
    assert response.status_code == 200
    data = response.json()
    nodes = data["nodes"]
    node_ids = {n["id"] for n in nodes}
    
    # "services/auth_service.py" matches. Its neighbors are "backend/api.py" (predecessor) and "db/models.py" (successor).
    assert "services/auth_service.py" in node_ids
    assert "backend/api.py" in node_ids
    assert "db/models.py" in node_ids
    
    # "services/retrieval_service.py" is not a neighbor of auth_service, so it should be excluded!
    assert "services/retrieval_service.py" not in node_ids


def test_graph_api_limits(setup_test_repo) -> None:
    """Verifies that limits are respected for large graphs."""
    repo_name, _ = setup_test_repo
    
    # We test local serialization with very low limits (max_nodes = 2)
    graph_service = GraphService()
    arch_service = ArchitectureService()
    
    graph_data = graph_service.get_visualization_graph(
        repo_name=repo_name,
        architecture_service=arch_service,
        max_nodes=2,
        max_edges=5
    )
    
    assert len(graph_data["nodes"]) == 2
    assert len(graph_data["edges"]) <= 5
