"""Tests for `services.github_review_renderer`."""

from __future__ import annotations

import pytest

from models.pr_intelligence import (
    ChangedFile,
    PRAnalysisResult,
    PropagationPath,
    ReviewFocusArea,
    RiskBreakdown,
    SymbolChange,
)
from services.github_review_renderer import (
    STICKY_MARKER,
    check_conclusion_for,
    render_check_summary,
    render_pr_review,
)


def _result(**overrides: object) -> PRAnalysisResult:
    """Builds a baseline PRAnalysisResult; tests override fields they care about."""
    base: dict = dict(
        repo="acme/widgets",
        pr_number=42,
        pr_url="https://github.com/acme/widgets/pull/42",
        pr_title="Refactor billing pipeline",
        pr_state="open",
        pr_size="M",
        risk_score=72,
        risk_level="HIGH",
        risk_breakdown=[
            RiskBreakdown(factor="Blast radius", score=30, detail="Wide downstream"),
            RiskBreakdown(factor="Churn", score=20, detail="High churn|file"),
        ],
        top_risks=["Touches billing core", "Breaks public API"],
        changed_files=[
            ChangedFile(
                filename="src/a.py",
                status="modified",
                additions=10,
                deletions=2,
                changes=12,
            ),
            ChangedFile(
                filename="src/b.py",
                status="added",
                additions=40,
                deletions=0,
                changes=40,
            ),
        ],
        total_additions=50,
        total_deletions=2,
        added_symbols=[
            SymbolChange(
                name="new_fn",
                type="function",
                file_path="src/b.py",
                line_number=10,
                language="python",
                change_type="added",
            ),
        ],
        modified_symbols=[],
        removed_symbols=[],
        affected_files=["src/a.py", "src/b.py"],
        impact_radius=5,
        blast_radius="HIGH",
        max_depth=3,
        propagation_paths=[
            PropagationPath(source="a", target="z", path=["a", "b", "z"], depth=2),
        ],
        affected_components=["billing"],
        changed_entry_points=["src/main.py"],
        changed_core_files=["src/a.py"],
        changed_high_coupling_files=[],
        review_focus_areas=[
            ReviewFocusArea(
                area="Billing core",
                reason="Touches payment paths",
                files=["src/a.py", "src/b.py", "src/c.py", "src/d.py"],
                priority="HIGH",
            ),
        ],
        analyzed_at="2026-06-22T10:00:00Z",
    )
    base.update(overrides)
    return PRAnalysisResult(**base)


def test_render_pr_review_starts_with_sticky_marker():
    body = render_pr_review(_result())
    assert body.startswith(STICKY_MARKER)


def test_render_pr_review_contains_core_signals():
    body = render_pr_review(_result())
    assert "Repository Intelligence Review" in body
    assert "#42 Refactor billing pipeline" in body
    assert "72/100" in body
    assert "🟠 HIGH" in body
    assert "+50 / −2" in body
    assert "Top Risk Factors" in body
    assert "Touches billing core" in body
    assert "Review Focus Areas" in body


def test_render_pr_review_escapes_pipes_in_breakdown_detail():
    body = render_pr_review(_result())
    # The "High churn|file" detail must not break the markdown table.
    assert "High churn\\|file" in body


def test_render_pr_review_truncates_focus_area_file_lists():
    # 4 files → preview shows 3, "+1 more"
    body = render_pr_review(_result())
    assert "(+1 more)" in body


def test_render_pr_review_handles_empty_optional_sections():
    body = render_pr_review(
        _result(
            top_risks=[],
            risk_breakdown=[],
            review_focus_areas=[],
            changed_entry_points=[],
            changed_core_files=[],
            changed_high_coupling_files=[],
        )
    )
    assert "Top Risk Factors" not in body
    assert "Risk Breakdown" not in body
    assert "Review Focus Areas" not in body
    assert "Critical Files Touched" not in body
    # Core risk header must still render.
    assert "Overall Risk" in body


def test_render_check_summary_includes_elapsed_and_link():
    summary = render_check_summary(
        _result(),
        elapsed_seconds=12.34,
        comment_url="https://github.com/acme/widgets/pull/42#issuecomment-1",
    )
    assert "12.3s" in summary
    assert "72/100" in summary
    assert "Full review comment" in summary
    assert "#issuecomment-1" in summary


def test_render_check_summary_without_link():
    summary = render_check_summary(_result(), elapsed_seconds=1.0)
    assert "Full review comment" not in summary


@pytest.mark.parametrize(
    "risk_level,expected",
    [
        ("LOW", "success"),
        ("MEDIUM", "neutral"),
        ("HIGH", "neutral"),
        ("CRITICAL", "neutral"),
        ("UNKNOWN", "neutral"),
    ],
)
def test_check_conclusion_for(risk_level, expected):
    assert check_conclusion_for(risk_level) == expected
