"""Churn data models for Git History & Churn Analysis.

Kept in a dedicated module separate from models/schemas.py to isolate
the churn domain and avoid touching existing model definitions.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class FileChurnRecord(BaseModel):
    """Churn statistics for a single file across the analysed commit window.

    Attributes:
        file_path:        Relative file path within the repository.
        commit_count:     Number of commits that touched this file.
        insertions:       Total lines inserted across all commits.
        deletions:        Total lines deleted across all commits.
        churn_score:      Normalised 0-100 score (higher = more churn).
        primary_author:   Email address of the author with the most commits.
        author_count:     Number of distinct contributors to this file.
        bus_factor_risk:  True when the primary author owns > 80 % of commits.
        last_commit_date: ISO-8601 UTC date of the most recent commit.
        is_deleted:       True if the file no longer exists at HEAD.
    """

    file_path: str = Field(..., description="Relative path within the repository.")
    commit_count: int = Field(0, ge=0, description="Number of commits touching this file.")
    insertions: int = Field(0, ge=0, description="Total lines inserted.")
    deletions: int = Field(0, ge=0, description="Total lines deleted.")
    churn_score: float = Field(0.0, ge=0.0, le=100.0, description="Normalised 0-100 churn score.")
    primary_author: str = Field("", description="Email of the top committer.")
    author_count: int = Field(0, ge=0, description="Number of distinct contributors.")
    bus_factor_risk: bool = Field(False, description="True when primary_author > 80 % ownership.")
    last_commit_date: str = Field("", description="ISO-8601 UTC date of the most recent commit.")
    is_deleted: bool = Field(False, description="True if the file is absent at HEAD.")


class HotspotFile(BaseModel):
    """A file that is both structurally central and historically high-churn.

    The composite hotspot_score combines churn_score and graph centrality so
    that a highly-churned peripheral file scores lower than a highly-churned
    core module.
    """

    file_path: str = Field(..., description="Relative path within the repository.")
    churn_score: float = Field(..., ge=0.0, le=100.0)
    centrality: float = Field(..., ge=0.0, le=1.0, description="Degree centrality from the dependency graph.")
    hotspot_score: float = Field(..., ge=0.0, description="Composite score = churn × (1 + centrality).")
    commit_count: int = Field(..., ge=0)
    primary_author: str = Field("")
    bus_factor_risk: bool = Field(False)


class TimelineEntry(BaseModel):
    """Commit activity aggregated into a weekly bucket.

    Attributes:
        week:          ISO-8601 date of the Monday that starts the week.
        commit_count:  Number of commits in this week.
        files_changed: Number of distinct files touched in this week.
        authors:       Distinct author emails active in this week.
    """

    week: str = Field(..., description="ISO-8601 Monday date of the week bucket.")
    commit_count: int = Field(0, ge=0)
    files_changed: int = Field(0, ge=0)
    authors: List[str] = Field(default_factory=list)


class AuthorOwnership(BaseModel):
    """Ownership breakdown for a single file.

    Attributes:
        file_path:       Relative file path.
        primary_author:  Email of the top committer.
        ownership_pct:   Fraction (0-100) of commits owned by primary_author.
        contributors:    Dict mapping author email → commit count.
    """

    file_path: str
    primary_author: str
    ownership_pct: float = Field(..., ge=0.0, le=100.0)
    contributors: Dict[str, int] = Field(default_factory=dict)


class ChurnSummary(BaseModel):
    """Full churn intelligence report for a repository.

    Written to data/churn/{owner}_{repo}_{since_days}.json by GitHistoryService.

    Attributes:
        repo:             Repository identifier (owner/repo).
        generated_at:     ISO-8601 UTC timestamp.
        since_days:       The commit-history window that was mined.
        total_commits:    Total commits analysed (merge commits excluded).
        total_files:      Number of distinct files appearing in history.
        hotspots:         Top files ranked by composite hotspot score.
        file_records:     Full per-file churn data (keyed by file_path).
        author_ownership: Per-file author ownership breakdown.
        timeline:         Weekly commit activity buckets.
        warning:          Optional warning (e.g. shallow clone detected).
    """

    repo: str
    generated_at: str
    since_days: int
    total_commits: int = Field(0, ge=0)
    total_files: int = Field(0, ge=0)
    hotspots: List[HotspotFile] = Field(default_factory=list)
    file_records: List[FileChurnRecord] = Field(default_factory=list)
    author_ownership: List[AuthorOwnership] = Field(default_factory=list)
    timeline: List[TimelineEntry] = Field(default_factory=list)
    warning: Optional[str] = None
