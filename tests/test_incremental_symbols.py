"""Unit tests for incremental SymbolService build (PH2-021)."""

import pytest
import os
import tempfile
import shutil

from services.symbol_service import SymbolService
from storage import JsonSnapshotStore
from core import AnalysisCache
from models.symbol import SymbolIndex


@pytest.fixture
def temp_store_and_service():
    tmpdir = tempfile.mkdtemp()
    store = JsonSnapshotStore(base_dir=tmpdir)
    cache = AnalysisCache()
    service = SymbolService(snapshot_store=store, analysis_cache=cache)
    yield service, store, tmpdir
    shutil.rmtree(tmpdir)


def test_symbol_service_incremental_updates(temp_store_and_service):
    """Verify that SymbolService.build_partial correctly retains, updates, and deletes symbols."""
    service, store, tmpdir = temp_store_and_service
    repo_name = "test/incremental_repo"
    
    # 1. Full Build
    files = [
        {"path": "main.py", "content": "def foo(): pass\ndef bar(): pass"},
        {"path": "utils.py", "content": "class Helper:\n    def run(self): pass"},
    ]
    
    full_result = service.build_full(repo_name, files=files)
    assert full_result["status"] == "success"
    assert full_result["symbol_count"] == 4  # foo, bar, Helper, run (methods are separate symbols)
    # wait! Let's check: Helper class, run method. Total symbols in utils.py = 2. Total in main.py = 2 (foo, bar). Total is 4!
    # Ah, let's load index and check actual symbols
    index = service.load(repo_name)
    assert index is not None
    symbol_names = {s.name for s in index.symbols}
    assert "foo" in symbol_names
    assert "bar" in symbol_names
    assert "Helper" in symbol_names
    assert "run" in symbol_names
    
    # 2. Partial Build (modify main.py: remove foo, add baz; delete utils.py)
    # changed_files: main.py, utils.py
    changed_files = {"main.py", "utils.py"}
    new_files = [
        {"path": "main.py", "content": "def bar(): pass\ndef baz(): pass"},
        # utils.py is deleted, so it's not in the new files list!
    ]
    
    partial_result = service.build_partial(repo_name, changed_files=changed_files, files=new_files)
    assert partial_result["status"] == "success"
    
    # Check updated index
    index_updated = service.load(repo_name)
    assert index_updated is not None
    
    updated_symbol_names = {s.name for s in index_updated.symbols}
    # "bar" is retained in main.py
    # "baz" is added in main.py
    # "foo" is removed from main.py
    # "Helper" and "run" are removed from utils.py (deleted)
    assert "bar" in updated_symbol_names
    assert "baz" in updated_symbol_names
    assert "foo" not in updated_symbol_names
    assert "Helper" not in updated_symbol_names
    assert "run" not in updated_symbol_names
    
    # Verify count
    assert len(index_updated.symbols) == 2
