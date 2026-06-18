"""Phase 2 — Repository Intelligence Layer: Pydantic models.

Defines output schemas for:
  - ReadingOrder    : optimal file-reading sequence for a developer
  - ImpactAnalysis  : files and components affected by a proposed change
  - ArchContext     : architecture context payload injected into LLM prompts

These models are intentionally separate from models/schemas.py and
models/architecture.py to keep phase boundaries clean.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Reading Order
# ---------------------------------------------------------------------------

class ReadingOrderEntry(BaseModel):
    """A single file in the recommended reading sequence.

    Attributes:
        rank:      1-based position in the reading order.
        file_path: Relative path to the file.
        reason:    Short human-readable justification for this rank.
        tier:      Broad category: 'entry_point', 'core', 'service', 'utility', 'other'.
        score:     Internal ranking score (higher = read sooner).
    """

    rank: int = Field(..., description="1-based position in the reading order.")
    file_path: str = Field(..., description="Relative file path.")
    reason: str = Field("", description="Why this file appears at this rank.")
    tier: str = Field("other", description="Tier category: entry_point, core, service, utility, other.")
    score: float = Field(0.0, description="Internal ranking score.")


class ReadingOrder(BaseModel):
    """Optimal code-reading sequence for a repository.

    Attributes:
        repo:                  Repository identifier (owner/repo).
        ordered_files:         Ranked list of ReadingOrderEntry items.
        reasoning:             Top-level explanation of the ranking strategy.
        estimated_reading_time: Approximate minutes to read all listed files.
        total_files_ranked:    Total number of files that were scored.
    """

    repo: str = Field(..., description="Repository identifier.")
    ordered_files: List[ReadingOrderEntry] = Field(
        default_factory=list,
        description="Files sorted from most-to-least important to read first.",
    )
    reasoning: List[str] = Field(
        default_factory=list,
        description="Bullet-point reasoning for the overall strategy.",
    )
    estimated_reading_time: int = Field(
        0,
        description="Estimated reading time in minutes.",
    )
    total_files_ranked: int = Field(
        0,
        description="Total number of source files considered.",
    )


# ---------------------------------------------------------------------------
# Impact Analysis
# ---------------------------------------------------------------------------

class DependencyPath(BaseModel):
    """A chain of files linking the changed file to an affected file.

    Attributes:
        path: List of file paths forming the dependency chain, from changed
              file to transitively affected file.
    """

    path: List[str] = Field(
        default_factory=list,
        description="Dependency chain: [changed_file, ..., affected_file].",
    )


class ImpactAnalysis(BaseModel):
    """Predicted impact of a change on the repository.

    Attributes:
        repo:                     Repository identifier.
        issue_text:               The original change request / issue.
        directly_affected_files:  Files that directly implement or import the
                                  changed functionality.
        indirectly_affected_files: Files transitively affected through the
                                  dependency graph.
        affected_components:      High-level component labels impacted.
        risk_level:               'low', 'medium', or 'high'.
        estimated_file_count:     Total count of directly + indirectly affected.
        dependency_paths:         Key dependency chains showing how impact spreads.
        confidence:               0–100 confidence score for this analysis.
    """

    repo: str = Field(..., description="Repository identifier.")
    issue_text: str = Field("", description="Original change request.")
    directly_affected_files: List[str] = Field(
        default_factory=list,
        description="Files directly touched by the change.",
    )
    indirectly_affected_files: List[str] = Field(
        default_factory=list,
        description="Files transitively affected through imports.",
    )
    affected_components: List[str] = Field(
        default_factory=list,
        description="High-level components impacted.",
    )
    risk_level: str = Field(
        "low",
        description="Risk level: low, medium, or high.",
    )
    estimated_file_count: int = Field(
        0,
        description="Total directly + indirectly affected files.",
    )
    dependency_paths: List[DependencyPath] = Field(
        default_factory=list,
        description="Key dependency chains illustrating how impact propagates.",
    )
    confidence: int = Field(
        0,
        ge=0,
        le=100,
        description="Confidence score 0–100.",
    )


# ---------------------------------------------------------------------------
# Architecture Context (used for LLM prompt injection)
# ---------------------------------------------------------------------------

class ArchContext(BaseModel):
    """Architecture context payload injected into LLM prompts.

    Attributes:
        entry_points:          Primary repository entry points.
        core_modules:          Most-central files by degree centrality.
        high_coupling_modules: Files with most combined in+out degree.
        total_files:           Total repository file count.
        total_dependencies:    Total import edges in the dependency graph.
        available:             False when no architecture has been built yet —
                               callers should degrade gracefully.
    """

    entry_points: List[str] = Field(default_factory=list)
    core_modules: List[str] = Field(default_factory=list)
    high_coupling_modules: List[str] = Field(default_factory=list)
    total_files: int = Field(0)
    total_dependencies: int = Field(0)
    available: bool = Field(
        False,
        description="True only when architecture data was successfully loaded.",
    )

    def to_prompt_block(self) -> str:
        """Render a compact, human-readable context block for LLM injection."""
        if not self.available:
            return ""
        lines = [
            "=== Repository Architecture Context ===",
            f"Total files: {self.total_files}  |  Dependency edges: {self.total_dependencies}",
            f"Entry points: {', '.join(self.entry_points[:5]) or 'none detected'}",
            f"Core modules (most connected): {', '.join(self.core_modules[:5]) or 'none'}",
            f"High-coupling files: {', '.join(self.high_coupling_modules[:5]) or 'none'}",
            "======================================",
        ]
        return "\n".join(lines)
