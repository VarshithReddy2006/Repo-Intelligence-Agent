"""Unit tests for Core Architecture Foundation (PH2-002)."""

import tempfile
import pytest

from core import (
    AnalysisCache,
    AnalysisRegistry,
    BuildPipeline,
)
from storage import JsonSnapshotStore


def test_analysis_cache():
    """Verify AnalysisCache read, write, invalidation, and statistics."""
    cache = AnalysisCache()
    cache.set("test/repo", "symbols", {"data": 123}, 1)

    # Valid get
    val = cache.get("test/repo", "symbols", 1)
    assert val == {"data": 123}

    # Stale get (should invalidate and return None)
    val_stale = cache.get("test/repo", "symbols", 2)
    assert val_stale is None
    assert cache.get("test/repo", "symbols", 1) is None

    # Stats check
    stats = cache.get_stats()
    assert stats["hits"]["symbols"] == 1
    assert stats["misses"]["symbols"] >= 1


def test_snapshot_store():
    """Verify JsonSnapshotStore persistence lifecycle."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = JsonSnapshotStore(base_dir=tmpdir)
        assert not store.exists("owner/repo", "symbols")

        payload = {"data": "test", "_schema_version": 1}
        store.save("owner/repo", "symbols", payload)
        assert store.exists("owner/repo", "symbols")

        loaded = store.load("owner/repo", "symbols")
        assert loaded["data"] == "test"

        store.delete("owner/repo", "symbols")
        assert not store.exists("owner/repo", "symbols")


def test_analysis_registry():
    """Verify AnalysisRegistry cycle detection and topological sorting."""
    registry = AnalysisRegistry()
    registry.register("A", type(None), dependencies=[], outputs=["a"])
    registry.register("B", type(None), dependencies=["A"], outputs=["b"])

    order = registry.get_topological_order()
    assert order == ["A", "B"]

    # Introduce dependency cycle: C depends on B, A depends on C
    registry.register("C", type(None), dependencies=["B"], outputs=["c"])
    registry.nodes["A"].dependencies.append("C")

    with pytest.raises(ValueError, match="Cycle detected"):
        registry.get_topological_order()


def test_build_pipeline():
    """Verify BuildPipeline runs steps in topological order and emits events."""
    registry = AnalysisRegistry()
    registry.register("A", type(None), dependencies=[], outputs=["a"])
    registry.register("B", type(None), dependencies=["A"], outputs=["b"])

    pipeline = BuildPipeline(registry)
    events = list(pipeline.build("test/repo", force_rebuild=True))

    # Assert basic start/end and step execution events
    assert events[0]["event"] == "START"
    assert any(e["event"] == "CACHE MISS" and e.get("node") == "A" for e in events)
    assert any(e["event"] == "SAVE" and e.get("node") == "A" for e in events)
    assert any(e["event"] == "BUILD TIME" and e.get("node") == "A" for e in events)
    assert events[-1]["event"] == "END"
