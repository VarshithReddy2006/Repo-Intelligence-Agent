import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class PRAnalyzeRequest(BaseModel):
    owner: Optional[str] = Field(None, description="GitHub repository owner")
    repo: Optional[str] = Field(None, description="GitHub repository name")
    pr_number: Optional[int] = Field(None, description="Pull request number")
    pr_url: Optional[str] = Field(None, description="Full GitHub Pull Request URL")

    @model_validator(mode="before")
    @classmethod
    def validate_request_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            pr_url = data.get("pr_url")
            if pr_url:
                # Parse and validate URL
                match = re.match(r"^https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)/?$", pr_url.strip())
                if not match:
                    raise ValueError("Invalid GitHub Pull Request URL format")
                data["owner"] = match.group(1)
                data["repo"] = match.group(2)
                data["pr_number"] = int(match.group(3))
            elif not all([data.get("owner"), data.get("repo"), data.get("pr_number")]):
                raise ValueError("Must provide either pr_url or all of owner, repo, and pr_number")
        return data


class ChangedFile(BaseModel):
    filename: str
    status: str          # added | removed | modified | renamed | copied
    additions: int
    deletions: int
    changes: int         # additions + deletions


class SymbolChange(BaseModel):
    name: str
    type: str            # function | class | method | interface | enum
    file_path: str
    line_number: int
    language: str
    change_type: str     # added | removed | modified
    parent_class: Optional[str] = None


class PropagationPath(BaseModel):
    source: str
    target: str
    path: List[str]
    depth: int


class RiskBreakdown(BaseModel):
    factor: str
    score: int
    detail: str


class ReviewFocusArea(BaseModel):
    area: str
    reason: str
    files: List[str]
    priority: str        # HIGH | MEDIUM | LOW


class PRAnalysisResult(BaseModel):
    repo: str
    pr_number: int
    pr_url: str
    pr_title: str
    pr_state: str
    pr_size: str                           # XS | S | M | L | XL
    risk_score: int                        # 0-100
    risk_level: str                        # LOW | MEDIUM | HIGH | CRITICAL
    risk_breakdown: List[RiskBreakdown]
    top_risks: List[str]                   # Max 5 top contributing risk factors
    changed_files: List[ChangedFile]
    total_additions: int
    total_deletions: int
    added_symbols: List[SymbolChange]
    modified_symbols: List[SymbolChange]
    removed_symbols: List[SymbolChange]
    affected_files: List[str]
    impact_radius: int
    blast_radius: str                      # LOW | MEDIUM | HIGH | EXTREME
    max_depth: int
    propagation_paths: List[PropagationPath]
    affected_components: List[str]
    changed_entry_points: List[str]
    changed_core_files: List[str]
    changed_high_coupling_files: List[str]
    review_focus_areas: List[ReviewFocusArea]
    analyzed_at: str                       # ISO-8601
