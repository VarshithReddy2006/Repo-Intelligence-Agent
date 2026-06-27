from datetime import datetime, timezone
import pytest

from models.report import (
    ReportDataModel,
    ReportMetadata,
    ScoreBreakdown,
    ArchReportSection,
    ApiReportSection,
    HygieneReportSection,
    OnboardingReportSection,
)
from services.report.renderer import HTMLRenderer, MarkdownRenderer, PDFRenderer


@pytest.fixture
def sample_report() -> ReportDataModel:
    """Fixture returning a filled ReportDataModel for testing renderers."""
    metadata = ReportMetadata(
        repo_name="org/test-repo",
        owner="org",
        name="test-repo",
        total_loc=5000,
        commits_count=120,
        languages={"python": 80.0, "javascript": 20.0},
        generated_at=datetime.now(timezone.utc).isoformat(),
        execution_time_ms=12.5,
    )
    scores = ScoreBreakdown(
        overall=88.5,
        architecture=90.0,
        api=85.0,
        hygiene=95.0,
        churn=80.0,
        readability=90.0,
        grade="B",
    )
    arch = ArchReportSection(
        cycles_count=1,
        cycles=[["core/utils.py", "core/logger.py"]],
        strongly_connected_components=2,
        smells_count=1,
        smells=["Cyclic import detected"],
    )
    api = ApiReportSection(
        total_exported_symbols=50,
        public_private_ratio=0.25,
        average_distance_main_sequence=0.12,
        unstable_modules_count=1,
    )
    hygiene = HygieneReportSection(
        dead_functions_count=5,
        dead_functions=["core/cache.py::stale_data"],
        dead_code_ratio=10.0,
    )
    onboarding = OnboardingReportSection(
        reading_path_completeness=90.0,
        core_entry_points=["main.py"],
        recommended_reading_path=["main.py", "core/utils.py"],
    )
    return ReportDataModel(
        metadata=metadata,
        scores=scores,
        architecture=arch,
        api_surface=api,
        hygiene=hygiene,
        onboarding=onboarding,
        refactoring_priorities=[
            "Refactor core/utils.py",
            "Remove unused core/cache.py::stale_data",
        ],
        ai_summary="This repository is well structured with clean code interfaces.",
    )


def test_html_renderer_generates_valid_output(sample_report):
    renderer = HTMLRenderer()
    html_bytes = renderer.render(sample_report)

    assert isinstance(html_bytes, bytes)
    html_str = html_bytes.decode("utf-8")

    # Check that core info is rendered
    assert "Repository Intelligence Report" in html_str
    assert "org/test-repo" in html_str
    assert "88.5" in html_str
    assert "Grade: B" in html_str

    # Check tabs exist
    assert 'id="overview"' in html_str
    assert 'id="architecture"' in html_str
    assert 'id="api"' in html_str
    assert 'id="hygiene"' in html_str
    assert 'id="walkthrough"' in html_str

    # Check variables are injected
    assert "5000" in html_str
    assert "120" in html_str
    assert "core/utils.py" in html_str
    assert "core/logger.py" in html_str
    assert "core/cache.py::stale_data" in html_str

    # Check that CSS and javascript are present
    assert "<style>" in html_str
    assert "function switchTab" in html_str


def test_markdown_renderer_generates_valid_output(sample_report):
    renderer = MarkdownRenderer()
    md_bytes = renderer.render(sample_report)

    assert isinstance(md_bytes, bytes)
    md_str = md_bytes.decode("utf-8")

    # Check main headings and report name
    assert "# Repository Health Report: org/test-repo" in md_str
    assert "## Health Summary" in md_str
    assert "88.5 / 100" in md_str
    assert "Grade: B" in md_str
    assert "## Refactoring Priorities" in md_str

    # Check that details collapsible blocks are present
    assert "<details>" in md_str
    assert "<summary><b>View Circular Import Paths</b></summary>" in md_str
    assert "<summary><b>View Design Smells Details</b></summary>" in md_str
    assert "<summary><b>View Dead Code Registry</b></summary>" in md_str
    assert "<summary><b>View Recommended Reading Order Guide</b></summary>" in md_str

    # Check variables are injected
    assert "5000" in md_str
    assert "120" in md_str
    assert "core/utils.py" in md_str
    assert "core/logger.py" in md_str
    assert "core/cache.py::stale_data" in md_str


def test_pdf_renderer_generates_valid_output(sample_report):
    renderer = PDFRenderer()
    pdf_html_bytes = renderer.render(sample_report)

    assert isinstance(pdf_html_bytes, bytes)
    pdf_html_str = pdf_html_bytes.decode("utf-8")

    # It must contain the regular HTML report content
    assert "Repository Intelligence Report" in pdf_html_str
    assert "org/test-repo" in pdf_html_str

    # And specifically it must contain the window.print() trigger
    assert "window.print()" in pdf_html_str
