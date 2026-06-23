"""Markdown renderer for PR analysis results.

Pure functions over `PRAnalysisResult` — no I/O, no logging side effects, no
network. The GitHub Action uses these to build the sticky comment and the
Check Run summary; the same renderer is reusable later for HTML/PDF reports
since the inputs are model objects and the outputs are plain strings.
"""
from __future__ import annotations

from typing import Optional

from models.pr_intelligence import PRAnalysisResult


# Hidden HTML marker that tags the sticky comment so subsequent runs can
# locate and update it instead of creating a duplicate.
STICKY_MARKER = "<!-- repo-intelligence-agent:sticky-comment -->"

# Hard cap on rows we inline in the changed-files table so the comment stays
# under GitHub's 65 KB body limit on huge PRs.
# ponytail: fixed cap; if PRs routinely overflow, switch to a separate gist link.
_MAX_FILE_ROWS = 50

_RISK_BADGES = {
    "LOW": "🟢 LOW",
    "MEDIUM": "🟡 MEDIUM",
    "HIGH": "🟠 HIGH",
    "CRITICAL": "🔴 CRITICAL",
}

_BLAST_BADGES = {
    "LOW": "🟢 LOW",
    "MEDIUM": "🟡 MEDIUM",
    "HIGH": "🟠 HIGH",
    "EXTREME": "🔴 EXTREME",
}


def render_pr_review(result: PRAnalysisResult) -> str:
    """Returns the full sticky-comment Markdown body, marker on the first line."""
    lines: list[str] = [
        STICKY_MARKER,
        "# Repository Intelligence Review",
        "",
        f"**PR:** [#{result.pr_number} {result.pr_title}]({result.pr_url}) · "
        f"`{result.pr_state}` · size **{result.pr_size}**",
        "",
        f"## Overall Risk: {_RISK_BADGES.get(result.risk_level, result.risk_level)} "
        f"({result.risk_score}/100)",
        "",
        f"- Blast radius: {_BLAST_BADGES.get(result.blast_radius, result.blast_radius)} "
        f"(impact radius {result.impact_radius}, max depth {result.max_depth})",
        f"- Changes: **+{result.total_additions} / −{result.total_deletions}** "
        f"across {len(result.changed_files)} files",
        f"- Symbols: +{len(result.added_symbols)} added · "
        f"~{len(result.modified_symbols)} modified · "
        f"−{len(result.removed_symbols)} removed",
        "",
    ]

    if result.top_risks:
        lines.append("### Top Risk Factors")
        for risk in result.top_risks[:5]:
            lines.append(f"- {risk}")
        lines.append("")

    if result.risk_breakdown:
        lines.append("<details><summary><b>Risk Breakdown</b></summary>")
        lines.append("")
        lines.append("| Factor | Score | Detail |")
        lines.append("|---|---:|---|")
        for rb in result.risk_breakdown:
            detail = rb.detail.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {rb.factor} | {rb.score} | {detail} |")
        lines.append("</details>")
        lines.append("")

    if result.review_focus_areas:
        lines.append("### Review Focus Areas")
        for area in result.review_focus_areas:
            lines.append(f"- **[{area.priority}] {area.area}** — {area.reason}")
            if area.files:
                files_preview = ", ".join(f"`{f}`" for f in area.files[:3])
                extra = f" (+{len(area.files) - 3} more)" if len(area.files) > 3 else ""
                lines.append(f"  - Files: {files_preview}{extra}")
        lines.append("")

    critical = (
        result.changed_entry_points
        or result.changed_core_files
        or result.changed_high_coupling_files
    )
    if critical:
        lines.append("<details><summary><b>Critical Files Touched</b></summary>")
        lines.append("")
        if result.changed_entry_points:
            lines.append(
                "**Entry points:** "
                + ", ".join(f"`{f}`" for f in result.changed_entry_points)
            )
            lines.append("")
        if result.changed_core_files:
            lines.append(
                "**Core files:** "
                + ", ".join(f"`{f}`" for f in result.changed_core_files)
            )
            lines.append("")
        if result.changed_high_coupling_files:
            lines.append(
                "**High-coupling files:** "
                + ", ".join(f"`{f}`" for f in result.changed_high_coupling_files)
            )
            lines.append("")
        lines.append("</details>")
        lines.append("")

    if result.changed_files:
        lines.append(
            f"<details><summary><b>Changed Files</b> ({len(result.changed_files)} total)"
            "</summary>"
        )
        lines.append("")
        lines.append("| File | Status | +/− |")
        lines.append("|---|---|---:|")
        for cf in result.changed_files[:_MAX_FILE_ROWS]:
            lines.append(
                f"| `{cf.filename}` | {cf.status} | +{cf.additions} / −{cf.deletions} |"
            )
        if len(result.changed_files) > _MAX_FILE_ROWS:
            remaining = len(result.changed_files) - _MAX_FILE_ROWS
            lines.append(f"| _… {remaining} more_ | | |")
        lines.append("</details>")
        lines.append("")

    lines.append(
        f"<sub>Analyzed at {result.analyzed_at} · repo `{result.repo}`</sub>"
    )
    return "\n".join(lines)


def render_check_summary(
    result: PRAnalysisResult,
    elapsed_seconds: float,
    comment_url: Optional[str] = None,
) -> str:
    """Short Markdown for the Check Run `output.summary` field."""
    parts = [
        f"**Risk:** {_RISK_BADGES.get(result.risk_level, result.risk_level)} "
        f"({result.risk_score}/100, blast {result.blast_radius})",
        f"**Changes:** +{result.total_additions} / −{result.total_deletions} "
        f"across {len(result.changed_files)} files",
        f"**Symbols:** +{len(result.added_symbols)} / "
        f"~{len(result.modified_symbols)} / −{len(result.removed_symbols)}",
        f"**Elapsed:** {elapsed_seconds:.1f}s",
    ]
    if comment_url:
        parts.append(f"[Full review comment →]({comment_url})")
    return "\n\n".join(parts)


# Maps risk level → GitHub Check Run conclusion.
# Defaults to advisory ("neutral") so the Action doesn't block merges on
# heuristic risk scores. Teams can wrap this in their own gating workflow.
_CONCLUSION_BY_RISK = {
    "LOW": "success",
    "MEDIUM": "neutral",
    "HIGH": "neutral",
    "CRITICAL": "neutral",
}


def check_conclusion_for(risk_level: str) -> str:
    """Returns a GitHub Check Run `conclusion` string for the given risk level."""
    return _CONCLUSION_BY_RISK.get(risk_level, "neutral")
