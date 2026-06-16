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
    assert "steps" in data
    assert len(data["steps"]) > 0
    assert "step_number" in data["steps"][0]
