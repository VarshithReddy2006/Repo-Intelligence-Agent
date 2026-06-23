"""Storage module exposing snapshot store implementations."""

from .snapshot_store import JsonSnapshotStore, SnapshotStore

__all__ = ["SnapshotStore", "JsonSnapshotStore"]
