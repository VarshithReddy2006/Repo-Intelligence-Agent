from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from backend.api import app
from backend.cli import app as cli_app
from models.report import ReportDataModel
from storage.migrations import run_migrations


@pytest.fixture(autouse=True)
def run_db_migrations():
    """Initializes migrations before running tests."""
    run_migrations()


@pytest.fixture
def mock_report_composer():
    """Creates a mock ReportComposer returning a dummy ReportDataModel."""
    report_json = {
        "metadata": {
            "repo_name": "org/test-repo",
            "owner": "org",
            "name": "test-repo",
            "total_loc": 5000,
            "commits_count": 120,
            "languages": {"python": 100.0},
            "generated_at": "2026-06-23T08:00:00Z",
            "execution_time_ms": 10.0,
        },
        "scores": {
            "overall": 88.5,
            "architecture": 90.0,
            "api": 85.0,
            "hygiene": 95.0,
            "churn": 80.0,
            "readability": 90.0,
            "grade": "B",
        },
        "architecture": {
            "cycles_count": 0,
            "cycles": [],
            "strongly_connected_components": 1,
            "smells_count": 0,
            "smells": [],
        },
        "api_surface": {
            "total_exported_symbols": 10,
            "public_private_ratio": 0.5,
            "average_distance_main_sequence": 0.15,
            "unstable_modules_count": 0,
        },
        "hygiene": {
            "dead_functions_count": 0,
            "dead_functions": [],
            "dead_code_ratio": 0.0,
        },
        "onboarding": {
            "reading_path_completeness": 100.0,
            "core_entry_points": ["main.py"],
            "recommended_reading_path": ["main.py"],
        },
        "refactoring_priorities": ["No priorities"],
        "ai_summary": "All clean",
    }
    report = ReportDataModel.model_validate(report_json)

    with patch("backend.routers.report.report_composer") as mock_comp:
        mock_comp.compose_report.return_value = report
        yield mock_comp


def test_api_build_report(mock_report_composer):
    client = TestClient(app)
    resp = client.post("/api/v1/report/org/test-repo/build")

    assert resp.status_code == 200
    data = resp.json()
    assert data["metadata"]["repo_name"] == "org/test-repo"
    assert data["scores"]["overall"] == 88.5
    assert data["scores"]["grade"] == "B"
    mock_report_composer.compose_report.assert_called_once_with("org/test-repo")


def test_api_get_report_summary(mock_report_composer):
    # First, let's trigger build to write to database
    client = TestClient(app)
    client.post("/api/v1/report/org/test-repo/build")

    # Query summary (should fetch from database)
    resp = client.get("/api/v1/report/org/test-repo/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["repo_name"] == "org/test-repo"
    assert data["score"] == 88.5
    assert data["grade"] == "B"


def test_api_download_report(mock_report_composer):
    client = TestClient(app)
    resp = client.get("/api/v1/report/org/test-repo/download?format=html")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"
    assert "attachment" in resp.headers["content-disposition"]
    assert "org_test-repo_report.html" in resp.headers["content-disposition"]
    assert "Repository Intelligence Report" in resp.text


def test_cli_report_command(tmp_path):
    runner = CliRunner()
    output_file = tmp_path / "custom_report.html"

    # We patch httpx requests made in CLI
    mock_build_resp = MagicMock(status_code=200)
    mock_build_resp.json.return_value = {"scores": {"overall": 88.5, "grade": "B"}}

    mock_down_resp = MagicMock(status_code=200, content=b"HTML Report Content")

    def mock_httpx_post(url, *args, **kwargs):
        if "build" in url:
            return mock_build_resp
        return MagicMock(status_code=404)

    def mock_httpx_get(url, *args, **kwargs):
        if "download" in url:
            return mock_down_resp
        return MagicMock(status_code=404)

    with (
        patch("httpx.post", side_effect=mock_httpx_post) as mock_post,
        patch("httpx.get", side_effect=mock_httpx_get) as mock_get,
    ):
        result = runner.invoke(
            cli_app,
            [
                "report",
                "org/test-repo",
                "--output-path",
                str(output_file),
                "--url",
                "http://mock-server",
            ],
        )

        assert result.exit_code == 0
        assert "Report composed successfully" in result.stdout
        assert "saved to" in result.stdout

        # Verify file is written
        assert output_file.exists()
        assert output_file.read_bytes() == b"HTML Report Content"

        mock_post.assert_called_once_with(
            "http://mock-server/api/v1/report/org/test-repo/build", timeout=60.0
        )
        mock_get.assert_called_once_with(
            "http://mock-server/api/v1/report/org/test-repo/download?format=html",
            timeout=30.0,
        )


def test_api_download_report_markdown(mock_report_composer):
    client = TestClient(app)
    resp = client.get("/api/v1/report/org/test-repo/download?format=markdown")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/markdown; charset=utf-8"
    assert "attachment" in resp.headers["content-disposition"]
    assert "org_test-repo_report.md" in resp.headers["content-disposition"]
    assert "# Repository Health Report: org/test-repo" in resp.text


def test_api_download_report_pdf(mock_report_composer):
    client = TestClient(app)
    resp = client.get("/api/v1/report/org/test-repo/download?format=pdf")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"
    assert "attachment" in resp.headers["content-disposition"]
    assert "org_test-repo_report.html" in resp.headers["content-disposition"]
    assert "window.print()" in resp.text


def test_cli_report_command_markdown(tmp_path):
    runner = CliRunner()
    output_file = tmp_path / "custom_report.md"

    # We patch httpx requests made in CLI
    mock_build_resp = MagicMock(status_code=200)
    mock_build_resp.json.return_value = {"scores": {"overall": 88.5, "grade": "B"}}

    mock_down_resp = MagicMock(status_code=200, content=b"Markdown Report Content")

    def mock_httpx_post(url, *args, **kwargs):
        if "build" in url:
            return mock_build_resp
        return MagicMock(status_code=404)

    def mock_httpx_get(url, *args, **kwargs):
        if "download" in url:
            return mock_down_resp
        return MagicMock(status_code=404)

    with (
        patch("httpx.post", side_effect=mock_httpx_post) as mock_post,
        patch("httpx.get", side_effect=mock_httpx_get) as mock_get,
    ):
        result = runner.invoke(
            cli_app,
            [
                "report",
                "org/test-repo",
                "--markdown",
                "--output-path",
                str(output_file),
                "--url",
                "http://mock-server",
            ],
        )

        assert result.exit_code == 0
        assert "Report composed successfully" in result.stdout
        assert "saved to" in result.stdout

        # Verify file is written
        assert output_file.exists()
        assert output_file.read_bytes() == b"Markdown Report Content"

        mock_post.assert_called_once_with(
            "http://mock-server/api/v1/report/org/test-repo/build", timeout=60.0
        )
        mock_get.assert_called_once_with(
            "http://mock-server/api/v1/report/org/test-repo/download?format=markdown",
            timeout=30.0,
        )
