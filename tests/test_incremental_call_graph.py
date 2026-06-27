"""Unit tests for incremental CallGraphService build (PH2-021)."""

import pytest
import tempfile
import shutil

from services.symbol_service import SymbolService
from services.architecture_service import ArchitectureService
from services.call_graph_service import CallGraphService
from storage import JsonSnapshotStore
from core import AnalysisCache, RepositoryContext


@pytest.fixture
def temp_store_and_services():
    tmpdir = tempfile.mkdtemp()
    store = JsonSnapshotStore(base_dir=tmpdir)
    cache = AnalysisCache()

    symbol_svc = SymbolService(snapshot_store=store, analysis_cache=cache)
    arch_svc = ArchitectureService(
        snapshot_store=store, analysis_cache=cache, graphs_dir=tmpdir
    )

    # Inject Mock GraphService into CallGraphService
    from services.graph_service import GraphService

    graph_svc = GraphService(graphs_dir=tmpdir)
    call_svc = CallGraphService(
        symbol_service=symbol_svc,
        graph_service=graph_svc,
        snapshot_store=store,
        analysis_cache=cache,
    )

    yield symbol_svc, arch_svc, call_svc, store, tmpdir
    shutil.rmtree(tmpdir)


def test_call_graph_service_incremental_updates(temp_store_and_services):
    """Verify that CallGraphService.build_partial correctly manages cached call edges and rebuilds call graph."""
    symbol_svc, arch_svc, call_svc, store, tmpdir = temp_store_and_services
    repo_name = "test/incremental_repo"

    # 1. Setup Symbol Index and Dependency Graph (Full)
    files = [
        {"path": "main.py", "content": "def run_main():\n    utils_foo()"},
        {"path": "utils.py", "content": "def utils_foo():\n    helper_bar()"},
        {"path": "helper.py", "content": "def helper_bar():\n    pass"},
    ]

    symbol_svc.build_full(repo_name, files=files)
    arch_svc.build_full(repo_name, files=files)

    context = RepositoryContext(
        repo_name,
        repo_path=tmpdir,
        cache=call_svc.analysis_cache,
        store=store,
        graph_service=call_svc.graph_service,
    )

    # 2. Build Call Graph (Full)
    gen = call_svc.build_full(repo_name, context=context, files=files)
    # consume generator
    events = list(gen)
    assert any(e["status"] == "complete" for e in events)

    # Check that call_edges snapshot is saved
    edges_snapshot = store.load(repo_name, "call_edges")
    assert edges_snapshot is not None
    assert len(edges_snapshot["edges"]) == 3

    # Check graph edges
    G = call_svc.load_graph(repo_name)
    assert G is not None
    # Node IDs are in format file_path::qualified_name
    nid_main = "main.py::run_main"
    nid_utils = "utils.py::utils_foo"
    nid_helper = "helper.py::helper_bar"
    assert G.has_edge(nid_main, nid_utils)
    assert G.has_edge(nid_utils, nid_helper)

    # 3. Partial Build: modify main.py to call helper_bar directly (bypass utils_foo)
    changed_files = {"main.py"}
    new_files = [
        {"path": "main.py", "content": "def run_main():\n    helper_bar()"},
        {"path": "utils.py", "content": "def utils_foo():\n    helper_bar()"},
        {"path": "helper.py", "content": "def helper_bar():\n    pass"},
    ]

    # Rebuild Symbol index and parsed files for main.py changes first
    symbol_svc.build_partial(repo_name, changed_files=changed_files, files=new_files)
    arch_svc.build_partial(repo_name, changed_files=changed_files, files=new_files)

    # Re-evaluate context
    context_updated = RepositoryContext(
        repo_name,
        repo_path=tmpdir,
        cache=call_svc.analysis_cache,
        store=store,
        graph_service=call_svc.graph_service,
    )

    # Build Call Graph (Partial)
    gen_partial = call_svc.build_partial(
        repo_name, changed_files=changed_files, context=context_updated, files=new_files
    )
    events_partial = list(gen_partial)
    assert any(e["status"] == "complete" for e in events_partial)

    # Verify that call_edges snapshot is updated
    edges_snapshot_updated = store.load(repo_name, "call_edges")
    assert len(edges_snapshot_updated["edges"]) == 3

    # Rebuild graph should show main.py -> helper_bar and utils.py -> helper_bar, but main.py -> utils_foo is removed
    G_updated = call_svc.load_graph(repo_name)
    assert G_updated is not None
    assert G_updated.has_edge(nid_main, nid_helper)
    assert G_updated.has_edge(nid_utils, nid_helper)
    assert not G_updated.has_edge(nid_main, nid_utils)
