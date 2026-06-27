"""PH2-002 Symbol Intelligence Layer — Unit Tests.

Covers:
  - SymbolService.build(): Python extraction (function, class, method)
  - SymbolService.build(): TypeScript extraction (interface, enum)
  - Line numbers are integers >= 1
  - save() + load() round-trip (SymbolIndex Pydantic model)
  - get_file_symbols(): filters by file path correctly
  - get_definition(): returns best match, returns None on miss
  - get_references(): returns all name matches (may be empty)
  - Missing repo handling: returns None gracefully (no crash)
  - API endpoints: GET /api/symbols/.../file/..., /definition/..., /references/...
"""

import os
import sys
import json
import tempfile
import shutil
import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.symbol_service import SymbolService
from models.symbol import SymbolIndex


# ===========================================================================
# Synthetic source content for deterministic testing
# ===========================================================================

PYTHON_CONTENT = """\
import os
from typing import List


class RetrievalService:
    def __init__(self, store):
        self.store = store

    def retrieve(self, query: str) -> List[str]:
        return []

    def _private(self):
        pass


def health_check():
    return True


def _helper(x, y):
    return x + y
"""


TS_CONTENT = """\
import { Injectable } from '@angular/core';

export interface UserProfile {
  id: number;
  name: string;
}

export enum Role {
  Admin,
  User,
  Guest,
}

export class UserService {
  constructor(private http: any) {}

  getUser(id: number): UserProfile {
    return {} as UserProfile;
  }
}

export function createUser(name: string): UserProfile {
  return { id: 0, name };
}
"""

JS_CONTENT = """\
import express from 'express';

class Router {
  constructor() {}

  addRoute(path, handler) {}
}

function startServer(port) {
  console.log('starting');
}

const middleware = (req, res) => {
  res.next();
};
"""


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture(scope="module")
def tmp_symbols_dir():
    """Isolated temporary directory for symbol indices — cleaned up after tests."""
    d = tempfile.mkdtemp(prefix="test_symbols_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def service(tmp_symbols_dir):
    """SymbolService instance pointing at the temp directory."""
    return SymbolService(symbols_dir=tmp_symbols_dir)


@pytest.fixture(scope="module")
def built_service(service):
    """Build a synthetic repo index once and share across all module tests."""
    files = [
        {"path": "services/retrieval_service.py", "content": PYTHON_CONTENT},
        {"path": "src/user.service.ts", "content": TS_CONTENT},
        {"path": "src/router.js", "content": JS_CONTENT},
        {"path": "README.md", "content": "# Docs — not parsed"},
    ]
    result = service.build("testorg/testrepo", files=files)
    return service, result


# ===========================================================================
# SymbolService.build() — basic result shape
# ===========================================================================


class TestBuild:
    def test_build_returns_success_status(self, built_service):
        _, result = built_service
        assert result["status"] == "success"

    def test_build_returns_repo_name(self, built_service):
        _, result = built_service
        assert result["repo"] == "testorg/testrepo"

    def test_build_reports_symbol_count(self, built_service):
        _, result = built_service
        # At least: 3 fns + 1 class + 3 methods (Python) +
        #           1 interface + 1 enum + 1 class + 2 methods + 1 fn (TS) +
        #           1 class + 2 methods + 1 fn + 1 arrow fn (JS) = 18+
        assert result["symbol_count"] >= 15

    def test_build_reports_files_indexed(self, built_service):
        _, result = built_service
        # README.md is ignored (unsupported extension)
        assert result["files_indexed"] == 3


# ===========================================================================
# Python symbol extraction
# ===========================================================================


class TestPythonExtraction:
    @pytest.fixture(scope="class")
    def py_symbols(self, built_service):
        service, _ = built_service
        syms = service.get_file_symbols(
            "testorg/testrepo", "services/retrieval_service.py"
        )
        assert syms is not None
        return syms

    def test_class_extracted(self, py_symbols):
        classes = [s for s in py_symbols if s.type == "class"]
        assert any(s.name == "RetrievalService" for s in classes)

    def test_function_extracted(self, py_symbols):
        fns = [s for s in py_symbols if s.type == "function"]
        fn_names = {s.name for s in fns}
        assert "health_check" in fn_names
        assert "_helper" in fn_names

    def test_methods_extracted_with_parent_class(self, py_symbols):
        methods = [s for s in py_symbols if s.type == "method"]
        method_names = {s.name for s in methods}
        assert "__init__" in method_names
        assert "retrieve" in method_names
        assert "_private" in method_names
        # All methods should report RetrievalService as parent
        for m in methods:
            assert m.parent_class == "RetrievalService"

    def test_line_numbers_are_positive_integers(self, py_symbols):
        for sym in py_symbols:
            assert isinstance(sym.line_number, int), f"{sym.name} line_number not int"
            assert sym.line_number >= 1, f"{sym.name} line_number < 1"

    def test_language_is_python(self, py_symbols):
        for sym in py_symbols:
            assert sym.language == "python"


# ===========================================================================
# TypeScript symbol extraction (interface + enum)
# ===========================================================================


class TestTypeScriptExtraction:
    @pytest.fixture(scope="class")
    def ts_symbols(self, built_service):
        service, _ = built_service
        syms = service.get_file_symbols("testorg/testrepo", "src/user.service.ts")
        assert syms is not None
        return syms

    def test_interface_extracted(self, ts_symbols):
        interfaces = [s for s in ts_symbols if s.type == "interface"]
        assert any(s.name == "UserProfile" for s in interfaces)

    def test_enum_extracted(self, ts_symbols):
        enums = [s for s in ts_symbols if s.type == "enum"]
        assert any(s.name == "Role" for s in enums)

    def test_class_extracted(self, ts_symbols):
        classes = [s for s in ts_symbols if s.type == "class"]
        assert any(s.name == "UserService" for s in classes)

    def test_function_extracted(self, ts_symbols):
        fns = [s for s in ts_symbols if s.type == "function"]
        assert any(s.name == "createUser" for s in fns)

    def test_method_has_parent_class(self, ts_symbols):
        methods = [s for s in ts_symbols if s.type == "method"]
        assert any(
            s.name == "getUser" and s.parent_class == "UserService" for s in methods
        )

    def test_line_numbers_are_positive_integers(self, ts_symbols):
        for sym in ts_symbols:
            assert sym.line_number >= 1

    def test_language_tag(self, ts_symbols):
        for sym in ts_symbols:
            assert sym.language == "typescript"


# ===========================================================================
# JavaScript symbol extraction
# ===========================================================================


class TestJavaScriptExtraction:
    @pytest.fixture(scope="class")
    def js_symbols(self, built_service):
        service, _ = built_service
        syms = service.get_file_symbols("testorg/testrepo", "src/router.js")
        assert syms is not None
        return syms

    def test_class_extracted(self, js_symbols):
        assert any(s.name == "Router" and s.type == "class" for s in js_symbols)

    def test_function_extracted(self, js_symbols):
        assert any(s.name == "startServer" and s.type == "function" for s in js_symbols)

    def test_arrow_function_extracted(self, js_symbols):
        assert any(s.name == "middleware" and s.type == "function" for s in js_symbols)

    def test_method_extracted(self, js_symbols):
        assert any(
            s.type == "method" and s.parent_class == "Router" for s in js_symbols
        )


# ===========================================================================
# Persistence — save() + load() round-trip
# ===========================================================================


class TestPersistence:
    def test_index_file_exists_on_disk(self, service, tmp_symbols_dir):
        path = os.path.join(tmp_symbols_dir, "testorg_testrepo.json")
        assert os.path.exists(path)

    def test_load_returns_symbol_index(self, service):
        index = service.load("testorg/testrepo")
        assert index is not None
        assert isinstance(index, SymbolIndex)

    def test_symbol_count_matches_build_result(self, service, built_service):
        _, build_result = built_service
        index = service.load("testorg/testrepo")
        assert index.symbol_count == build_result["symbol_count"]
        assert len(index.symbols) == build_result["symbol_count"]

    def test_index_has_correct_repo_name(self, service):
        index = service.load("testorg/testrepo")
        assert index.repo == "testorg/testrepo"

    def test_index_has_generated_at_timestamp(self, service):
        index = service.load("testorg/testrepo")
        assert index.generated_at  # non-empty ISO string
        assert "T" in index.generated_at  # ISO-8601 format

    def test_json_file_has_schema_version(self, tmp_symbols_dir):
        path = os.path.join(tmp_symbols_dir, "testorg_testrepo.json")
        with open(path) as fh:
            data = json.load(fh)
        assert "_schema_version" in data
        assert data["_schema_version"] >= 1

    def test_index_exists_returns_true(self, service):
        assert service.index_exists("testorg/testrepo") is True

    def test_index_exists_returns_false_for_unknown_repo(self, service):
        assert service.index_exists("no/repo") is False


# ===========================================================================
# Query methods
# ===========================================================================


class TestQueryMethods:
    def test_get_file_symbols_filters_correctly(self, built_service):
        service, _ = built_service
        syms = service.get_file_symbols(
            "testorg/testrepo", "services/retrieval_service.py"
        )
        assert syms is not None
        for s in syms:
            assert s.file_path == "services/retrieval_service.py"

    def test_get_file_symbols_returns_empty_list_for_unknown_file(self, built_service):
        service, _ = built_service
        syms = service.get_file_symbols("testorg/testrepo", "nonexistent/file.py")
        assert syms is not None  # index exists, file just has no symbols
        assert isinstance(syms, list)
        assert len(syms) == 0

    def test_get_file_symbols_returns_none_for_missing_repo(self, service):
        result = service.get_file_symbols("no/repo", "any/file.py")
        assert result is None

    def test_get_definition_finds_class(self, built_service):
        service, _ = built_service
        sym = service.get_definition("testorg/testrepo", "RetrievalService")
        assert sym is not None
        assert sym.name == "RetrievalService"
        assert sym.type == "class"

    def test_get_definition_finds_function(self, built_service):
        service, _ = built_service
        sym = service.get_definition("testorg/testrepo", "health_check")
        assert sym is not None
        assert sym.type == "function"

    def test_get_definition_returns_none_for_unknown_symbol(self, built_service):
        service, _ = built_service
        sym = service.get_definition("testorg/testrepo", "nonexistent_fn_xyz")
        assert sym is None

    def test_get_definition_returns_none_for_missing_repo(self, service):
        sym = service.get_definition("no/repo", "anything")
        assert sym is None

    def test_get_references_returns_list(self, built_service):
        service, _ = built_service
        refs = service.get_references("testorg/testrepo", "RetrievalService")
        assert refs is not None
        assert isinstance(refs, list)
        assert len(refs) >= 1

    def test_get_references_empty_for_nonexistent_symbol(self, built_service):
        service, _ = built_service
        refs = service.get_references("testorg/testrepo", "no_such_symbol_xyz")
        assert refs is not None
        assert refs == []

    def test_get_references_returns_none_for_missing_repo(self, service):
        refs = service.get_references("no/repo", "anything")
        assert refs is None


# ===========================================================================
# API endpoint tests
# ===========================================================================


class TestSymbolAPIEndpoints:
    """Tests against the live FastAPI app via TestClient."""

    @pytest.fixture(scope="class")
    def client_with_index(self, tmp_symbols_dir):
        """Build a test symbol index in the real service's storage, then return a TestClient."""
        from fastapi.testclient import TestClient

        # Build the index using the app's own symbol_service so the endpoint
        # can find it without mocking.
        from backend.api import app, symbol_service

        files = [
            {"path": "services/auth.py", "content": PYTHON_CONTENT},
        ]
        symbol_service.build("apitest/repo", files=files)

        client = TestClient(app)
        yield client

    def test_file_endpoint_returns_200(self, client_with_index):
        r = client_with_index.get("/api/symbols/apitest/repo/file/services/auth.py")
        assert r.status_code == 200
        body = r.json()
        assert "symbols" in body
        assert "symbol_count" in body
        assert body["file"] == "services/auth.py"
        assert body["symbol_count"] >= 1

    def test_file_endpoint_404_on_missing_repo(self, client_with_index):
        r = client_with_index.get("/api/symbols/no/repo/file/any/file.py")
        assert r.status_code == 404

    def test_definition_endpoint_returns_200(self, client_with_index):
        r = client_with_index.get(
            "/api/symbols/apitest/repo/definition/RetrievalService"
        )
        assert r.status_code == 200
        body = r.json()
        assert body["symbol"] == "RetrievalService"
        assert "definition" in body
        assert body["definition"]["type"] == "class"

    def test_definition_endpoint_404_on_unknown_symbol(self, client_with_index):
        r = client_with_index.get(
            "/api/symbols/apitest/repo/definition/nonexistent_xyz"
        )
        assert r.status_code == 404

    def test_definition_endpoint_404_on_missing_repo(self, client_with_index):
        r = client_with_index.get("/api/symbols/no/repo/definition/anything")
        assert r.status_code == 404

    def test_references_endpoint_returns_200(self, client_with_index):
        r = client_with_index.get("/api/symbols/apitest/repo/references/health_check")
        assert r.status_code == 200
        body = r.json()
        assert "references" in body
        assert "reference_count" in body
        assert "note" in body
        assert body["reference_count"] >= 1

    def test_references_endpoint_returns_empty_list_for_unknown(
        self, client_with_index
    ):
        r = client_with_index.get(
            "/api/symbols/apitest/repo/references/nonexistent_xyz"
        )
        assert r.status_code == 200
        body = r.json()
        assert body["reference_count"] == 0
        assert body["references"] == []

    def test_references_endpoint_404_on_missing_repo(self, client_with_index):
        r = client_with_index.get("/api/symbols/no/repo/references/anything")
        assert r.status_code == 404
