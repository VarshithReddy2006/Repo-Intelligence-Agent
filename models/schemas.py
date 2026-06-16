"""Shared schemas using Pydantic for the Repo Intelligence Agent.

These schemas act as standard data exchange formats between agents,
memory layers, and the user interface.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class RepositoryAnalysis(BaseModel):
    """Schema representing repository analysis output.

    Attributes:
        structure: A dictionary representing the file/directory tree structure.
        dependencies: A list of detected package/library dependencies.
        tech_stack: A list of detected frameworks, languages, and technologies.
        metadata: Optional additional metadata about the repository.
    """

    structure: Dict[str, Optional[List[str]]] = Field(
        ..., description="File and folder tree structure map."
    )
    dependencies: List[str] = Field(
        default_factory=list, description="List of libraries and packages detected."
    )
    tech_stack: List[str] = Field(
        default_factory=list, description="Detected frameworks and languages."
    )
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Metadata key-value pairs of the analysis."
    )


class ComponentRelationship(BaseModel):
    """Schema representing relationship between code components."""

    source: str = Field(..., description="Source component name or path.")
    target: str = Field(..., description="Target component name or path.")
    relationship_type: str = Field(
        ..., description="Type of relationship (e.g., imports, calls, inherits)."
    )
    description: str = Field(
        ..., description="Explanation of how the components interact."
    )


class ArchitectureSummary(BaseModel):
    """Schema representing architecture explanation output.

    Attributes:
        summary: A high-level description of the system architecture.
        reading_order: Recommended file reading order for a new developer.
        relationships: Component interaction and dependencies list.
    """

    summary: str = Field(..., description="High-level architectural summary.")
    reading_order: List[str] = Field(
        default_factory=list, description="Recommended file-by-file reading order."
    )
    relationships: List[ComponentRelationship] = Field(
        default_factory=list, description="Inter-component relationships."
    )


class ImplementationPlanStep(BaseModel):
    """Schema representing a single step in an implementation plan."""

    step_number: int = Field(..., description="Sequence number of the step.")
    description: str = Field(..., description="Detail of what needs to be changed.")
    files_to_modify: List[str] = Field(
        ..., description="Files targeted in this specific step."
    )


class ImplementationPlan(BaseModel):
    """Schema representing the issue mapping and planning output.

    Attributes:
        issue_summary: Brief description of the issue being addressed.
        relevant_files: List of files identified as relevant to the issue.
        steps: Step-by-step modification guide.
    """

    issue_summary: str = Field(..., description="Summary of the user issue.")
    relevant_files: List[str] = Field(
        ..., description="Files involved or requiring modifications."
    )
    steps: List[ImplementationPlanStep] = Field(
        ..., description="Ordered steps to implement the change/fix."
    )


class EvaluationResult(BaseModel):
    """Schema representing the quality evaluation result of agent responses.

    Attributes:
        citations_valid: True if citations map to actual source lines correctly.
        hallucination_detected: True if response statements lack source support.
        confidence_score: Score between 0.0 and 1.0 indicating response accuracy.
        feedback: Detailed reasoning or suggestions for correction.
    """

    citations_valid: bool = Field(
        ..., description="Indicates if references are valid and exist."
    )
    hallucination_detected: bool = Field(
        ..., description="Indicates if unsupported statements are present."
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0."
    )
    feedback: str = Field(..., description="Detailed feedback of the evaluation.")
