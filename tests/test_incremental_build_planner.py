"""Unit tests for IncrementalBuildPlanner and BuildTask generation (PH2-021)."""

import pytest
from core.analysis_registry import AnalysisRegistry
from core.change_detector import ChangeSet
from core.incremental_build_planner import IncrementalBuildPlanner
from models.build_manifest import BuildManifest


class MockSnapshotStore:
    def __init__(self, existing_keys=None):
        self.existing_keys = existing_keys or set()

    def exists(self, repo_name, key, subkey=None):
        if subkey:
            return f"{key}:{subkey}" in self.existing_keys
        return key in self.existing_keys


class MockGraphService:
    def __init__(self, existing_graphs=None):
        self.existing_graphs = existing_graphs or set()

    def graph_exists(self, repo_name):
        return repo_name in self.existing_graphs


@pytest.fixture
def registry():
    reg = AnalysisRegistry()
    reg.register(
        "Symbol Index",
        type(None),
        dependencies=[],
        outputs=["symbols"],
        schema_version=1,
    )
    reg.register(
        "Dependency Graph",
        type(None),
        dependencies=["Symbol Index"],
        outputs=["graphs/dependency"],
        schema_version=1,
    )
    reg.register(
        "Call Graph",
        type(None),
        dependencies=["Symbol Index", "Dependency Graph"],
        outputs=["graphs/call"],
        schema_version=1,
    )
    return reg


def test_plan_first_build(registry):
    """Verify first build plans all tasks in FULL mode."""
    change_set = ChangeSet(
        added={"main.py"},
        modified=set(),
        deleted=set(),
        renamed={},
        unchanged=set(),
        repository_changed=True,
    )
    store = MockSnapshotStore()
    graphs = MockGraphService()

    tasks = IncrementalBuildPlanner.plan(
        repo_name="test/repo",
        change_set=change_set,
        registry=registry,
        old_manifest=None,
        snapshot_store=store,
        graph_service=graphs,
    )

    assert len(tasks) == 3
    assert all(t.mode == "FULL" for t in tasks)


def test_plan_no_change_skip(registry):
    """Verify no-change rebuild plans all tasks in SKIP mode."""
    change_set = ChangeSet(
        added=set(),
        modified=set(),
        deleted=set(),
        renamed={},
        unchanged={"main.py"},
        repository_changed=False,
    )
    # Mock snapshots exist
    store = MockSnapshotStore({"symbols", "graphs/call"})
    graphs = MockGraphService(
        {"test/repo", "test/repo_call_graph"}
    )  # Both graphs exist

    manifest = BuildManifest(
        repository_hash="repo_hash",
        file_hashes={"main.py": "hash123"},
        schema_versions={"Symbol Index": 1, "Dependency Graph": 1, "Call Graph": 1},
    )

    tasks = IncrementalBuildPlanner.plan(
        repo_name="test/repo",
        change_set=change_set,
        registry=registry,
        old_manifest=manifest,
        snapshot_store=store,
        graph_service=graphs,
    )

    assert len(tasks) == 3
    assert all(t.mode == "SKIP" for t in tasks)


def test_plan_code_change_partial(registry):
    """Verify code change plans all tasks in PARTIAL mode."""
    change_set = ChangeSet(
        added=set(),
        modified={"main.py"},
        deleted=set(),
        renamed={},
        unchanged=set(),
        repository_changed=True,
    )
    # Mock snapshots exist
    store = MockSnapshotStore({"symbols", "graphs/call"})
    graphs = MockGraphService({"test/repo", "test/repo_call_graph"})

    manifest = BuildManifest(
        repository_hash="old_repo_hash",
        file_hashes={"main.py": "old_hash"},
        schema_versions={"Symbol Index": 1, "Dependency Graph": 1, "Call Graph": 1},
    )

    tasks = IncrementalBuildPlanner.plan(
        repo_name="test/repo",
        change_set=change_set,
        registry=registry,
        old_manifest=manifest,
        snapshot_store=store,
        graph_service=graphs,
    )

    assert len(tasks) == 3
    assert all(t.mode == "PARTIAL" for t in tasks)
    assert tasks[0].changed_files == {"main.py"}


def test_plan_stale_schema_rebuild(registry):
    """Verify stale schema version triggers FULL rebuild for that task and downstream."""
    change_set = ChangeSet(
        added=set(),
        modified=set(),
        deleted=set(),
        renamed={},
        unchanged={"main.py"},
        repository_changed=False,
    )
    store = MockSnapshotStore({"symbols", "graphs/call"})
    graphs = MockGraphService({"test/repo", "test/repo_call_graph"})

    # Manifest schema version for Symbol Index is 1, but registry expects 2
    registry.nodes["Symbol Index"].schema_version = 2

    manifest = BuildManifest(
        repository_hash="repo_hash",
        file_hashes={"main.py": "hash123"},
        schema_versions={"Symbol Index": 1, "Dependency Graph": 1, "Call Graph": 1},
    )

    tasks = IncrementalBuildPlanner.plan(
        repo_name="test/repo",
        change_set=change_set,
        registry=registry,
        old_manifest=manifest,
        snapshot_store=store,
        graph_service=graphs,
    )

    # Symbol Index (stale version) -> FULL
    assert tasks[0].analysis == "Symbol Index"
    assert tasks[0].mode == "FULL"

    # Dependency Graph (depends on Symbol Index which runs FULL) -> PARTIAL
    assert tasks[1].analysis == "Dependency Graph"
    assert tasks[1].mode == "PARTIAL"

    # Call Graph (depends on Dependency Graph which runs PARTIAL) -> PARTIAL
    assert tasks[2].analysis == "Call Graph"
    assert tasks[2].mode == "PARTIAL"


def test_plan_missing_snapshot_rebuild(registry):
    """Verify missing snapshot triggers FULL rebuild for that task."""
    change_set = ChangeSet(
        added=set(),
        modified=set(),
        deleted=set(),
        renamed={},
        unchanged={"main.py"},
        repository_changed=False,
    )
    # Symbol Index exists, but Dependency Graph (graph_exists) is missing!
    store = MockSnapshotStore({"symbols", "graphs/call"})
    graphs = MockGraphService({"test/repo_call_graph"})  # only call graph exists

    manifest = BuildManifest(
        repository_hash="repo_hash",
        file_hashes={"main.py": "hash123"},
        schema_versions={"Symbol Index": 1, "Dependency Graph": 1, "Call Graph": 1},
    )

    tasks = IncrementalBuildPlanner.plan(
        repo_name="test/repo",
        change_set=change_set,
        registry=registry,
        old_manifest=manifest,
        snapshot_store=store,
        graph_service=graphs,
    )

    # Symbol Index -> SKIP (exists and up to date)
    assert tasks[0].analysis == "Symbol Index"
    assert tasks[0].mode == "SKIP"

    # Dependency Graph -> FULL (missing snapshot)
    assert tasks[1].analysis == "Dependency Graph"
    assert tasks[1].mode == "FULL"

    # Call Graph -> PARTIAL (depends on Dependency Graph which runs FULL)
    assert tasks[2].analysis == "Call Graph"
    assert tasks[2].mode == "PARTIAL"
