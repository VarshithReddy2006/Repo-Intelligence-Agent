"""Unit tests verifying real implementations and interface for memory storage classes."""

import pytest
import os
from memory import ChromaStore, SQLiteStore, FileCache


def test_chroma_store_real(tmp_path) -> None:
    """Verifies ChromaStore can be instantiated and executes indexing and retrieval correctly."""
    persist_dir = str(tmp_path / "test_chroma")
    store = ChromaStore(persist_directory=persist_dir)
    assert store.persist_directory == persist_dir

    # 1. Add chunks using add_code_chunks
    store.add_code_chunks(
        file_path="src/utils.py",
        chunks=["def add(a, b): return a + b", "def sub(a, b): return a - b"],
        embeddings=[[0.1] * 3072, [0.2] * 3072],
        metadata=[{"line": 1, "fn": "add"}, {"line": 2, "fn": "sub"}]
    )

    # 2. Search similar
    results = store.search_similar(query_embedding=[0.1] * 3072, limit=1)
    assert len(results) == 1
    assert "src/utils.py" in results[0]["id"]
    assert results[0]["metadata"]["fn"] == "add"

    # 3. Test index_repository
    dummy_chunks = [
        {"path": "auth.py", "chunk_id": 1, "content": "def login(): pass", "language": "python"},
        {"path": "auth.py", "chunk_id": 2, "content": "def logout(): pass", "language": "python"}
    ]
    dummy_embeddings = [[0.5] * 3072, [0.6] * 3072]
    store.index_repository("test/repo", dummy_chunks, dummy_embeddings)

    # 4. Search repository
    repo_results = store.search_repository("test/repo", query_embedding=[0.5] * 3072, limit=1)
    assert len(repo_results) == 1
    assert repo_results[0]["metadata"]["repo_name"] == "test/repo"
    assert repo_results[0]["metadata"]["file_path"] == "auth.py"

    # 5. Delete repository
    store.delete_repository("test/repo")
    repo_results_after = store.search_repository("test/repo", query_embedding=[0.5] * 3072, limit=1)
    assert len(repo_results_after) == 0

    # 6. Clear database
    store.clear_database()


def test_sqlite_store_init() -> None:
    """Verifies SQLiteStore can be instantiated and raises NotImplementedError for unimplemented methods."""
    store = SQLiteStore(db_path="dummy_path.db")
    assert store.db_path == "dummy_path.db"

    with pytest.raises(NotImplementedError):
        store.init_tables()


def test_file_cache_init() -> None:
    """Verifies FileCache can be instantiated and raises NotImplementedError for unimplemented methods."""
    cache = FileCache(cache_file="dummy_cache.json")
    assert cache.cache_file == "dummy_cache.json"

    with pytest.raises(NotImplementedError):
        cache.get("key")
