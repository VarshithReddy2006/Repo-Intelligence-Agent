"""Unit tests verifying import and initialization interface for memory storage classes."""

import pytest
from memory import ChromaStore, SQLiteStore, FileCache


def test_chroma_store_init() -> None:
    """Verifies ChromaStore can be instantiated and raises NotImplementedError for unimplemented methods."""
    store = ChromaStore(persist_directory="dummy_dir")
    assert store.persist_directory == "dummy_dir"

    with pytest.raises(NotImplementedError):
        store.add_code_chunks("path", [], [], [])

    with pytest.raises(NotImplementedError):
        store.search_similar([])

    with pytest.raises(NotImplementedError):
        store.clear_database()


def test_sqlite_store_init() -> None:
    """Verifies SQLiteStore can be instantiated and raises NotImplementedError for unimplemented methods."""
    store = SQLiteStore(db_path="dummy_path.db")
    assert store.db_path == "dummy_path.db"

    with pytest.raises(NotImplementedError):
        store.init_tables()

    with pytest.raises(NotImplementedError):
        store.save_repository_meta("repo", {})

    with pytest.raises(NotImplementedError):
        store.log_query("repo", "query", "response")

    with pytest.raises(NotImplementedError):
        store.save_issue_plan("issue", {})

    with pytest.raises(NotImplementedError):
        store.get_query_history("repo")


def test_file_cache_init() -> None:
    """Verifies FileCache can be instantiated and raises NotImplementedError for unimplemented methods."""
    cache = FileCache(cache_file="dummy_cache.json")
    assert cache.cache_file == "dummy_cache.json"

    with pytest.raises(NotImplementedError):
        cache.get("key")

    with pytest.raises(NotImplementedError):
        cache.set("key", "value")

    with pytest.raises(NotImplementedError):
        cache.delete("key")

    with pytest.raises(NotImplementedError):
        cache.clear()
