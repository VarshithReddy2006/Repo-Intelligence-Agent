"""API Surface Intelligence data models.

Uses Python enums for all categorical values to eliminate raw-string bugs
and make exhaustive-match checking possible in tests.

Kept in a dedicated module following the existing convention:
  models/churn.py, models/call_graph.py, models/symbol.py, etc.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Visibility(str, Enum):
    """How broadly a symbol is accessible."""
    PUBLIC   = "public"    # exported / part of the module's public interface
    INTERNAL = "internal"  # used within the package but not exported
    PRIVATE  = "private"   # convention-private (underscore prefix, etc.)
    UNKNOWN  = "unknown"   # could not be determined with sufficient confidence


class ApiKind(str, Enum):
    """What role the API plays in the system."""
    EXPORTED        = "exported"        # explicit export statement (JS/TS)
    ROUTE           = "route"           # HTTP route handler (FastAPI, Flask, Express)
    CLI_ENTRY       = "cli_entry"       # CLI command entry point
    MAIN_ENTRY      = "main_entry"      # __main__ or if __name__ == '__main__'
    PUBLIC_CLASS    = "public_class"    # exported / non-private class
    PUBLIC_FUNCTION = "public_function" # exported / non-private top-level function
    PUBLIC_METHOD   = "public_method"   # non-private method of a public class
    INTERFACE       = "interface"       # TypeScript interface
    ENUM_TYPE       = "enum_type"       # TypeScript / Python enum
    INTERNAL_HELPER = "internal_helper" # internal function/method not part of public surface
    UNKNOWN         = "unknown"


class ApiStatus(str, Enum):
    """Lifecycle status of an API."""
    STABLE       = "stable"
    DEPRECATED   = "deprecated"   # annotated as deprecated
    EXPERIMENTAL = "experimental" # annotated as experimental / beta
    UNKNOWN      = "unknown"


class BreakingChangeKind(str, Enum):
    """Type of breaking change detected."""
    REMOVED_EXPORT    = "removed_export"    # public symbol removed entirely
    RENAMED_EXPORT    = "renamed_export"    # likely rename (remove + add with similar name)
    SIGNATURE_CHANGED = "signature_changed" # param count changed
    VISIBILITY_REDUCED = "visibility_reduced" # was public, now private/internal


# ---------------------------------------------------------------------------
# Core classification unit
# ---------------------------------------------------------------------------

class ClassifiedSymbol(BaseModel):
    """A symbol from the Symbol Index enriched with API surface metadata.

    Attributes:
        name:                  Symbol name.
        qualified:             Dot-qualified name (Class.method or function).
        symbol_type:           function | class | method | interface | enum.
        file_path:             Relative file path.
        line_number:           1-indexed definition line.
        language:              Source language.
        parent_class:          Enclosing class for methods.
        visibility:            PUBLIC | INTERNAL | PRIVATE | UNKNOWN.
        api_kind:              Categorical role.
        status:                STABLE | DEPRECATED | EXPERIMENTAL | UNKNOWN.
        confidence:            0.0–1.0 classification confidence.
        classification_reason: Human-readable explanation of the classification.
        param_count:           Number of formal parameters (for breaking-change detection).
        is_async:              True if the function/method is declared async.
        decorators:            Decorator names found on this symbol (best-effort).
        fan_in:                Number of distinct callers from the call graph (0 if unavailable).
        is_orphan:             True when visibility=PUBLIC but fan_in=0 (unused public API).
    """

    name: str
    qualified: str
    symbol_type: str
    file_path: str
    line_number: int = 1
    language: str = "unknown"
    parent_class: Optional[str] = None

    visibility: Visibility = Visibility.UNKNOWN
    api_kind: ApiKind = ApiKind.UNKNOWN
    status: ApiStatus = ApiStatus.UNKNOWN
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    classification_reason: str = ""

    param_count: int = 0
    is_async: bool = False
    decorators: List[str] = Field(default_factory=list)

    fan_in: int = 0
    is_orphan: bool = False


# ---------------------------------------------------------------------------
# Breaking change record
# ---------------------------------------------------------------------------

class BreakingChange(BaseModel):
    """A single breaking API change between two surface snapshots.

    Attributes:
        kind:                Type of change.
        symbol_name:         Affected symbol name.
        file_path:           File path (from the before snapshot, or after for additions).
        before_param_count:  Parameter count before the change (None if not applicable).
        after_param_count:   Parameter count after the change.
        severity:            "high" | "medium" | "low".
        description:         Human-readable explanation.
    """

    kind: BreakingChangeKind
    symbol_name: str
    file_path: str = ""
    before_param_count: Optional[int] = None
    after_param_count: Optional[int] = None
    severity: str = "high"
    description: str = ""


# ---------------------------------------------------------------------------
# Summary / persisted report
# ---------------------------------------------------------------------------

class APISurfaceStats(BaseModel):
    """Aggregate statistics for one API surface report."""

    total_symbols: int = 0
    public_count: int = 0
    internal_count: int = 0
    private_count: int = 0
    unknown_count: int = 0
    deprecated_count: int = 0
    experimental_count: int = 0
    route_count: int = 0
    entry_point_count: int = 0
    orphan_public_count: int = 0
    by_language: Dict[str, int] = Field(default_factory=dict)


class APISurface(BaseModel):
    """Full API surface report for a repository.

    Written to data/api_surface/{owner}_{repo}.json by APISurfaceService.

    Attributes:
        repo:         Repository identifier (owner/repo).
        generated_at: ISO-8601 UTC timestamp.
        symbols:      All classified symbols.
        stats:        Aggregate statistics.
        warning:      Optional diagnostic message.
    """

    repo: str
    generated_at: str
    symbols: List[ClassifiedSymbol] = Field(default_factory=list)
    stats: APISurfaceStats = Field(default_factory=APISurfaceStats)
    warning: Optional[str] = None
