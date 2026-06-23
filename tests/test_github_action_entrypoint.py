"""Tests for the GitHub Action entrypoint (`.github/actions/repo-intelligence/entrypoint.py`).

We load the module via importlib because it lives outside the import path,
then exercise the `GitHub` helper and `fetch_pr_analysis` with `httpx.MockTransport`
fixtures — no real network and no real `PRIntelligenceService` involvement.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Callable

import httpx
import pytest

from services.github_review_renderer import STICKY_MARKER


_ENTRYPOINT_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github" / "actions" / "repo-intelligence" / "entrypoint.py"
)


def _load_entrypoint():
    spec = importlib.util.spec_from_file_location(
        "repo_intel_action_entrypoint", _ENTRYPOINT_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


entrypoint = _load_entrypoint()


# -- httpx fixtures --------------------------------------------------------

def _mock_client(handler: Callable[[httpx.Request], httpx.Response],
                 base_url: str = "https://api.github.com") -> httpx.Client:
    return httpx.Client(
        base_url=base_url,
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer test"},
    )


def _comment(comment_id: int, body: str) -> dict:
    return {
        "id": comment_id,
        "body": body,
        "html_url": f"https://github.com/x/y/pull/1#issuecomment-{comment_id}",
    }


# -- fetch_pr_analysis -----------------------------------------------------

def _pr_analysis_payload() -> dict:
    return {
        "repo": "acme/widgets",
        "pr_number": 7,
        "pr_url": "https://github.com/acme/widgets/pull/7",
        "pr_title": "T",
        "pr_state": "open",
        "pr_size": "S",
        "risk_score": 10,
        "risk_level": "LOW",
        "risk_breakdown": [],
        "top_risks": [],
        "changed_files": [],
        "total_additions": 0,
        "total_deletions": 0,
        "added_symbols": [],
        "modified_symbols": [],
        "removed_symbols": [],
        "affected_files": [],
        "impact_radius": 0,
        "blast_radius": "LOW",
        "max_depth": 0,
        "propagation_paths": [],
        "affected_components": [],
        "changed_entry_points": [],
        "changed_core_files": [],
        "changed_high_coupling_files": [],
        "review_focus_areas": [],
        "analyzed_at": "2026-06-22T10:00:00Z",
    }


def test_fetch_pr_analysis_posts_to_correct_endpoint_with_bearer_token():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json=_pr_analysis_payload())

    client = _mock_client(handler, base_url="https://api.example.com")
    result = entrypoint.fetch_pr_analysis(
        "https://api.example.com/", "acme", "widgets", 7,
        api_token="secret", client=client,
    )

    assert result.risk_level == "LOW"
    assert captured["url"].endswith("/api/v1/pr/analyze")
    assert captured["auth"] == "Bearer secret"
    assert captured["body"] == {"owner": "acme", "repo": "widgets", "pr_number": 7}


def test_fetch_pr_analysis_raises_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = _mock_client(handler, base_url="https://api.example.com")
    with pytest.raises(httpx.HTTPStatusError):
        entrypoint.fetch_pr_analysis(
            "https://api.example.com", "a", "b", 1, client=client,
        )


# -- GitHub.find_sticky_comment -------------------------------------------

def test_find_sticky_comment_returns_matching_entry():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[
            _comment(1, "no marker here"),
            _comment(2, f"{STICKY_MARKER}\nbody"),
        ])

    gh = entrypoint.GitHub("tok", client=_mock_client(handler))
    found = gh.find_sticky_comment("o", "r", 1)
    assert found is not None
    assert found["id"] == 2


def test_find_sticky_comment_returns_none_when_absent():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[_comment(1, "hi"), _comment(2, "bye")])

    gh = entrypoint.GitHub("tok", client=_mock_client(handler))
    assert gh.find_sticky_comment("o", "r", 1) is None


def test_find_sticky_comment_paginates():
    pages = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        pages["count"] += 1
        if pages["count"] == 1:
            # full page → triggers next request
            body = [_comment(i, "filler") for i in range(100)]
        else:
            body = [_comment(999, f"{STICKY_MARKER}\nupdated")]
        return httpx.Response(200, json=body)

    gh = entrypoint.GitHub("tok", client=_mock_client(handler))
    found = gh.find_sticky_comment("o", "r", 1)
    assert pages["count"] == 2
    assert found is not None
    assert found["id"] == 999


# -- GitHub.upsert_sticky_comment -----------------------------------------

def test_upsert_sticky_comment_patches_existing():
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, str(request.url)))
        if request.method == "GET":
            return httpx.Response(200, json=[_comment(42, f"{STICKY_MARKER}\nold")])
        if request.method == "PATCH":
            return httpx.Response(200, json=_comment(42, "updated"))
        return httpx.Response(500)

    gh = entrypoint.GitHub("tok", client=_mock_client(handler))
    result = gh.upsert_sticky_comment("o", "r", 1, "new body")

    methods = [m for m, _ in calls]
    assert methods == ["GET", "PATCH"]
    assert "/issues/comments/42" in calls[1][1]
    assert result["id"] == 42


def test_upsert_sticky_comment_posts_when_none_exists():
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, str(request.url)))
        if request.method == "GET":
            return httpx.Response(200, json=[])
        if request.method == "POST":
            return httpx.Response(201, json=_comment(7, "new"))
        return httpx.Response(500)

    gh = entrypoint.GitHub("tok", client=_mock_client(handler))
    result = gh.upsert_sticky_comment("o", "r", 1, "body")

    methods = [m for m, _ in calls]
    assert methods == ["GET", "POST"]
    assert "/issues/1/comments" in calls[1][1]
    assert result["id"] == 7


# -- GitHub.create_check_run ----------------------------------------------

def test_create_check_run_posts_completed_status():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(201, json={"id": 99})

    gh = entrypoint.GitHub("tok", client=_mock_client(handler))
    gh.create_check_run(
        "o", "r", "abc123",
        name="Repository Intelligence",
        conclusion="neutral",
        title="Risk HIGH (72/100)",
        summary="**Risk:** HIGH",
    )

    assert captured["method"] == "POST"
    assert "/check-runs" in captured["url"]
    body = captured["body"]
    assert body["head_sha"] == "abc123"
    assert body["status"] == "completed"
    assert body["conclusion"] == "neutral"
    assert body["output"]["title"] == "Risk HIGH (72/100)"
