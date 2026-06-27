"""Strongly-typed build event models for execution tracking (PH2-022)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BuildEvent:
    """Base class for all build pipeline events."""

    event_type: str
    repo_name: str
    timestamp: float = field(default_factory=time.time)
    node: Optional[str] = None
    message: Optional[str] = None
    duration_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary matching legacy event schemas."""
        d = {
            "event": self.event_type,
            "repo_name": self.repo_name,
            "timestamp": self.timestamp,
        }
        if self.node is not None:
            d["node"] = self.node
        if self.message is not None:
            d["message"] = self.message
        if self.duration_ms is not None:
            d["duration_ms"] = self.duration_ms
        return d


# ---------------------------------------------------------------------------
# New Concurrency Staging Events
# ---------------------------------------------------------------------------


@dataclass
class TaskQueued(BuildEvent):
    """Event emitted when a task is scheduled in the execution queue."""

    def __init__(self, repo_name: str, node: str) -> None:
        super().__init__(
            event_type="TASK_QUEUED",
            repo_name=repo_name,
            node=node,
        )


@dataclass
class TaskStarted(BuildEvent):
    """Event emitted when a worker thread begins executing a task."""

    def __init__(self, repo_name: str, node: str) -> None:
        super().__init__(
            event_type="TASK_STARTED",
            repo_name=repo_name,
            node=node,
        )


@dataclass
class TaskCompleted(BuildEvent):
    """Event emitted when a task completes successfully."""

    def __init__(self, repo_name: str, node: str, duration_ms: float) -> None:
        super().__init__(
            event_type="TASK_COMPLETED",
            repo_name=repo_name,
            node=node,
            duration_ms=duration_ms,
        )


@dataclass
class TaskSkipped(BuildEvent):
    """Event emitted when a task is skipped (e.g. cache hit)."""

    def __init__(self, repo_name: str, node: str) -> None:
        super().__init__(
            event_type="TASK_SKIPPED",
            repo_name=repo_name,
            node=node,
        )


@dataclass
class TaskFailed(BuildEvent):
    """Event emitted when a task fails during execution."""

    def __init__(self, repo_name: str, node: str, error_message: str) -> None:
        super().__init__(
            event_type="TASK_FAILED",
            repo_name=repo_name,
            node=node,
            message=error_message,
        )


@dataclass
class StageCompleted(BuildEvent):
    """Event emitted when all tasks in a parallel stage have finished."""

    stage_index: int = 0
    tasks: List[str] = field(default_factory=list)

    def __init__(self, repo_name: str, stage_index: int, tasks: List[str]) -> None:
        super().__init__(
            event_type="STAGE_COMPLETED",
            repo_name=repo_name,
            message=f"Stage {stage_index} completed with tasks: {', '.join(tasks)}",
        )
        self.stage_index = stage_index
        self.tasks = tasks

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["stage_index"] = self.stage_index
        d["tasks"] = self.tasks
        return d


@dataclass
class BuildCompleted(BuildEvent):
    """Event emitted when the entire parallel build process finishes."""

    def __init__(self, repo_name: str, duration_ms: float) -> None:
        super().__init__(
            event_type="BUILD_COMPLETED",
            repo_name=repo_name,
            duration_ms=duration_ms,
        )


# ---------------------------------------------------------------------------
# Legacy Mapping Events (Backward Compatibility)
# ---------------------------------------------------------------------------


@dataclass
class StartEvent(BuildEvent):
    def __init__(self, repo_name: str) -> None:
        super().__init__(event_type="START", repo_name=repo_name)


@dataclass
class CacheHitEvent(BuildEvent):
    def __init__(self, repo_name: str, node: str) -> None:
        super().__init__(event_type="CACHE HIT", repo_name=repo_name, node=node)


@dataclass
class LoadEvent(BuildEvent):
    def __init__(self, repo_name: str, node: str) -> None:
        super().__init__(event_type="LOAD", repo_name=repo_name, node=node)


@dataclass
class CacheMissEvent(BuildEvent):
    def __init__(self, repo_name: str, node: str) -> None:
        super().__init__(event_type="CACHE MISS", repo_name=repo_name, node=node)


@dataclass
class ProgressEvent(BuildEvent):
    def __init__(self, repo_name: str, node: str, message: str) -> None:
        super().__init__(
            event_type="PROGRESS", repo_name=repo_name, node=node, message=message
        )


@dataclass
class SaveEvent(BuildEvent):
    def __init__(self, repo_name: str, node: str) -> None:
        super().__init__(event_type="SAVE", repo_name=repo_name, node=node)


@dataclass
class BuildTimeEvent(BuildEvent):
    def __init__(self, repo_name: str, node: str, duration_ms: float) -> None:
        super().__init__(
            event_type="BUILD TIME",
            repo_name=repo_name,
            node=node,
            duration_ms=duration_ms,
        )


@dataclass
class EndEvent(BuildEvent):
    def __init__(self, repo_name: str, duration_ms: float) -> None:
        super().__init__(event_type="END", repo_name=repo_name, duration_ms=duration_ms)


@dataclass
class ErrorEvent(BuildEvent):
    def __init__(
        self, repo_name: str, message: str, node: Optional[str] = None
    ) -> None:
        super().__init__(
            event_type="ERROR", repo_name=repo_name, node=node, message=message
        )
