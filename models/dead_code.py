from typing import List, Optional
from pydantic import BaseModel, Field


class DeadFile(BaseModel):
    file_path: str = Field(..., description="Path of the unused file relative to repo root")
    confidence: float = Field(..., description="Confidence score from 0.0 to 1.0")
    risk_level: str = Field(..., description="Risk of removing: SAFE | REVIEW | DANGEROUS")
    recommendation: str = Field(..., description="Actionable recommendation for developers")


class OrphanModule(BaseModel):
    file_path: str = Field(..., description="Path of the orphaned file relative to repo root")
    confidence: float = Field(..., description="Confidence score from 0.0 to 1.0")
    risk_level: str = Field(..., description="Risk of removing: SAFE | REVIEW | DANGEROUS")
    recommendation: str = Field(..., description="Actionable recommendation for developers")
    last_reachable_parent: Optional[str] = Field(
        None, description="Nearest active file that previously imported this module / subtree"
    )


class DeadDependencyChain(BaseModel):
    chain: List[str] = Field(..., description="List of file paths forming the dead import chain")
    confidence: float = Field(..., description="Confidence score from 0.0 to 1.0")
    risk_level: str = Field(..., description="Risk of removing: SAFE | REVIEW | DANGEROUS")
    recommendation: str = Field(..., description="Actionable recommendation for developers")
    length: int = Field(..., description="Number of hops in the chain")
    total_nodes: int = Field(..., description="Total number of nodes in the chain")
    max_centrality: float = Field(..., description="Maximum centrality among nodes in the chain")


class DeadCodeRequest(BaseModel):
    owner: str = Field(..., description="GitHub owner of the repository")
    repo: str = Field(..., description="GitHub name of the repository")


class DeadCodeResult(BaseModel):
    repo: str = Field(..., description="Repository owner/name identifier")
    cleanup_score: int = Field(..., ge=0, le=100, description="Overall health score (0-100)")
    previous_cleanup_score: Optional[int] = Field(
        None, description="Previous score if analysis has run before"
    )
    estimated_cleanup_effort: str = Field(..., description="Effort level: LOW | MEDIUM | HIGH")
    unused_files: List[DeadFile] = Field(default_factory=list, description="Unused root files")
    orphan_modules: List[OrphanModule] = Field(default_factory=list, description="Orphaned modules")
    dead_dependency_chains: List[DeadDependencyChain] = Field(
        default_factory=list, description="Chains of unreachable dependencies"
    )
    cleanup_recommendations: List[str] = Field(
        default_factory=list, description="Sorted natural language recommendations"
    )
    analyzed_at: str = Field(..., description="ISO-8601 UTC timestamp of analysis")
