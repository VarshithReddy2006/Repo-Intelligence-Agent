"""Unit tests for the FastAPI backend endpoints."""

import sys
import os
import pytest
from fastapi.testclient import TestClient

# Ensure root directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api import app

client = TestClient(app)


def test_get_examples() -> None:
    """Verifies example repos list is returned correctly."""
    response = client.get("/api/repos/examples")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "name" in data[0]
    assert "url" in data[0]


def test_get_recent() -> None:
    """Verifies recent repos list returns empty or populated list."""
    response = client.get("/api/repos/recent")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_map_issue() -> None:
    """Verifies issue mapping endpoint works and returns plan structure."""
    payload = {
        "repo": "test/repo",
        "title": "Fix memory leaks in cache",
        "description": "The cache store is leaking reference counts."
    }
    response = client.post("/api/issues/map", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "issue_summary" in data
    assert "relevant_files" in data
    assert "implementation_plan" in data
    assert "issue_type" in data
    assert "complexity" in data
    assert "confidence" in data
    assert "verified" in data
    assert "sources" in data
    assert "affected_components" in data


def test_index_invalid_repo_url_returns_400() -> None:
    """Invalid GitHub repo URL should not crash and should return 4xx."""
    response = client.post("/api/index", json={"repo_url": "hello"})
    assert response.status_code in (400, 422)


def test_index_nonexistent_repo_returns_404() -> None:
    """Nonexistent repository should map to 404 not 500."""
    response = client.post("/api/index", json={"repo_url": "https://github.com/this-repo-should-not-exist-1234567890/does-not-exist"})
    # Depending on environment/network, 404 mapping should happen; otherwise this test may fail.
    assert response.status_code in (404,)
