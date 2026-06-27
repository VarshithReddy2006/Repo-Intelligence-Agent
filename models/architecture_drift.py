import re
from typing import Any, List, Optional
from pydantic import BaseModel, Field, model_validator


class PRDriftRequest(BaseModel):
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
                match = re.match(
                    r"^https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)/?$",
                    pr_url.strip(),
                )
                if not match:
                    raise ValueError("Invalid GitHub Pull Request URL format")
                data["owner"] = match.group(1)
                data["repo"] = match.group(2)
                data["pr_number"] = int(match.group(3))
            elif not all([data.get("owner"), data.get("repo"), data.get("pr_number")]):
                raise ValueError(
                    "Must provide either pr_url or all of owner, repo, and pr_number"
                )
        return data


class DependencyEdge(BaseModel):
    source: str
    target: str


class CouplingChange(BaseModel):
    file: str
    before: int
    after: int


class PRDriftResult(BaseModel):
    repo: str
    pr_number: int
    architecture_risk_score: int
    architecture_risk_level: str
    architecture_improvement_score: int
    top_findings: List[str]
    drift_categories: List[str]
    architectural_hotspots: List[str]
    added_dependencies: List[DependencyEdge]
    removed_dependencies: List[DependencyEdge]
    new_cycles: List[List[str]]
    resolved_cycles: List[List[str]]
    coupling_increase: List[CouplingChange]
    coupling_decrease: List[CouplingChange]
    new_entry_points: List[str]
    removed_entry_points: List[str]
    analyzed_at: str
