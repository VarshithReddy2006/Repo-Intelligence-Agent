import os
import pytest
from backend.settings import settings
from storage.migrations import run_migrations, get_db_connection, get_applied_versions


@pytest.fixture(autouse=True)
def temp_db_path(tmp_path, monkeypatch):
    # Override settings.sqlite_db_path to a temporary file
    db_file = tmp_path / "test_repo_understanding.db"
    monkeypatch.setattr(settings, "sqlite_db_path", str(db_file))
    yield
    # Cleanup database file after test
    if db_file.exists():
        try:
            os.remove(db_file)
        except OSError:
            pass


def test_run_migrations_initializes_db():
    # Verify DB file doesn't exist yet
    assert not os.path.exists(settings.sqlite_db_path)

    # Run migrations
    run_migrations()

    # Verify DB file is created
    assert os.path.exists(settings.sqlite_db_path)

    # Verify table schema exists and migration version is recorded
    conn = get_db_connection()
    try:
        applied = get_applied_versions(conn)
        assert 1 in applied

        # Query repositories table to ensure it was created
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='repositories'"
        )
        assert cursor.fetchone() is not None
    finally:
        conn.close()


def test_migrations_are_idempotent():
    # Run migrations first time
    run_migrations()

    # Run migrations second time (should be idempotent and not fail)
    run_migrations()

    # Count how many migration files exist
    from storage.migrations import MIGRATIONS_DIR

    expected_count = 0
    if os.path.exists(MIGRATIONS_DIR):
        expected_count = len(
            [f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql")]
        )

    conn = get_db_connection()
    try:
        applied = get_applied_versions(conn)
        assert len(applied) == expected_count
        for i in range(1, expected_count + 1):
            assert i in applied
    finally:
        conn.close()
