"""Shared schemas and models package for the Repo Intelligence Agent."""

from .schemas import (
    RepositoryAnalysis,
    ArchitectureSummary,
    ComponentRelationship,
    ImplementationPlan,
    ImplementationPlanStep,
    EvaluationResult,
    IssueMapResponse,
)
from .architecture import (
    ParsedFile,
    GraphNode,
    GraphEdge,
    ArchitectureSummary as ArchitectureIntelSummary,
)
from .phase2 import (
    ReadingOrderEntry,
    ReadingOrder,
    DependencyPath,
    ImpactAnalysis,
    ArchContext,
)

__all__ = [
    # Existing schemas
    "RepositoryAnalysis",
    "ArchitectureSummary",
    "ComponentRelationship",
    "ImplementationPlan",
    "ImplementationPlanStep",
    "EvaluationResult",
    "IssueMapResponse",
    # Phase 1 — Architecture Foundation
    "ParsedFile",
    "GraphNode",
    "GraphEdge",
    "ArchitectureIntelSummary",
    # Phase 2 — Repository Intelligence
    "ReadingOrderEntry",
    "ReadingOrder",
    "DependencyPath",
    "ImpactAnalysis",
    "ArchContext",
]
