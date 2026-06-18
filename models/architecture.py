"""Architecture data models for Phase 1 — Architecture Foundation.

These Pydantic models represent the output structures of the architecture
intelligence pipeline.  They are kept separate from models/schemas.py to
avoid touching existing schemas and to keep the architecture domain isolated.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ParsedFile(BaseModel):
    """Metadata extracted from a single parsed source file.

    Attributes:
        file_path:  Relative path to the file within the repository.
        language:   Canonical language name (python, javascript, typescript, tsx).
        imports:    List of module/package names imported by this file.
        classes:    List of class definitions with name, base classes, and methods.
        functions:  List of top-level function definitions with name and parameters.
    """

    file_path: str = Field(..., description="Relative path to the file.")
    language: str = Field(..., description="Detected programming language.")
    imports: List[str] = Field(
        default_factory=list,
        description="Imported module or package names.",
    )
    classes: List[dict] = Field(
        default_factory=list,
        description=(
            "Classes defined in the file.  Each dict contains: "
            "class_name (str), base_classes (list[str]), methods (list[str])."
        ),
    )
    functions: List[dict] = Field(
        default_factory=list,
        description=(
            "Top-level functions defined in the file.  Each dict contains: "
            "function_name (str), parameters (list[str])."
        ),
    )


class GraphNode(BaseModel):
    """A node in a dependency graph.

    Attributes:
        id:    Unique identifier (file path or module name).
        type:  Node category: 'file' or 'module'.
        label: Human-readable display label.
    """

    id: str = Field(..., description="Unique node identifier.")
    type: str = Field(..., description="Node type: 'file' or 'module'.")
    label: str = Field(..., description="Human-readable label for the node.")


class GraphEdge(BaseModel):
    """A directed edge in a dependency graph.

    Attributes:
        source:       Source node id.
        target:       Target node id.
        relationship: Edge type (e.g. 'imports', 'depends_on').
    """

    source: str = Field(..., description="Source node identifier.")
    target: str = Field(..., description="Target node identifier.")
    relationship: str = Field(..., description="Type of relationship between nodes.")


class ArchitectureSummary(BaseModel):
    """High-level architecture metadata computed from the dependency graph.

    All fields are derived locally via graph analysis — no LLM required.

    Attributes:
        entry_points:           Files identified as primary entry points.
        core_modules:           Files/modules with highest degree centrality.
        high_coupling_modules:  Files/modules with the highest combined
                                in-degree + out-degree (most dependencies).
        total_files:            Total number of files in the repository.
        total_dependencies:     Total number of dependency edges in the graph.
    """

    entry_points: List[str] = Field(
        default_factory=list,
        description="Detected repository entry points.",
    )
    core_modules: List[str] = Field(
        default_factory=list,
        description="Most central modules by degree centrality.",
    )
    high_coupling_modules: List[str] = Field(
        default_factory=list,
        description="Modules with the highest total dependency count.",
    )
    total_files: int = Field(
        0,
        description="Total files in the repository.",
    )
    total_dependencies: int = Field(
        0,
        description="Total dependency edges in the file graph.",
    )
