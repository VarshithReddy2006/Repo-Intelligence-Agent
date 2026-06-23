"""Build Manifest model for incremental indexing (PH2-002, PH2-021)."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator


class BuildManifest(BaseModel):
    """Manifest representing the details of a repository analysis build."""

    repository_hash: str = Field(
        ..., description="MD5/SHA hash of repository content or revision ID."
    )
    schema_version: int = Field(
        default=1, description="Overall schema version of the analysis."
    )
    schema_versions: Dict[str, int] = Field(
        default_factory=dict,
        description="Map of analysis components to their schema versions.",
    )
    snapshot_versions: Dict[str, int] = Field(
        default_factory=dict,
        description="Map of analysis outputs to their schema versions.",
    )
    tree_sitter_version: str = Field(
        default="0.20.0", description="Version of tree-sitter parser library used."
    )
    embedding_model: str = Field(
        default="unknown", description="Name of the LLM/embedding model used."
    )
    embedding_schema: int = Field(
        default=1, description="Version of embedding database schema."
    )
    embedding_schema_version: int = Field(
        default=1, description="Version of embedding database schema."
    )
    graph_schema: int = Field(
        default=1, description="Schema version of serialization graph."
    )
    graph_schema_version: int = Field(
        default=1, description="Schema version of serialization graph."
    )
    build_timestamps: Dict[str, float] = Field(
        default_factory=dict,
        description="Map of component names to build epoch timestamps.",
    )
    file_hashes: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of file relative paths to content hashes.",
    )
    dependency_versions: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of dependency library names to their installed versions.",
    )
    application_version: str = Field(
        default="1.0.0", description="Version of the analysis application."
    )
    last_successful_build: Optional[float] = Field(
        None, description="Epoch timestamp of last successful build."
    )
    build_duration_ms: float = Field(
        default=0.0, description="Total build time in milliseconds."
    )

    @model_validator(mode="before")
    @classmethod
    def migrate_older_manifests(cls, data: Any) -> Any:
        """Automatically migrate old manifest dictionary structures."""
        if not isinstance(data, dict):
            return data

        # Migrate schema_version -> schema_versions
        if "schema_version" in data and "schema_versions" not in data:
            val = data["schema_version"]
            data["schema_versions"] = {"global": val}
        elif "schema_versions" in data and not isinstance(data["schema_versions"], dict):
            data["schema_versions"] = {"global": data["schema_versions"]}

        # Migrate embedding_schema <-> embedding_schema_version
        if "embedding_schema" in data and "embedding_schema_version" not in data:
            data["embedding_schema_version"] = data["embedding_schema"]
        elif "embedding_schema_version" in data and "embedding_schema" not in data:
            data["embedding_schema"] = data["embedding_schema_version"]

        # Migrate graph_schema <-> graph_schema_version
        if "graph_schema" in data and "graph_schema_version" not in data:
            data["graph_schema_version"] = data["graph_schema"]
        elif "graph_schema_version" in data and "graph_schema" not in data:
            data["graph_schema"] = data["graph_schema_version"]

        # Provide defaults for new fields
        if "application_version" not in data:
            data["application_version"] = "1.0.0"
        if "build_duration_ms" not in data:
            data["build_duration_ms"] = 0.0

        return data
