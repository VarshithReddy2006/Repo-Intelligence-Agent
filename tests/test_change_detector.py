"""Unit tests for ChangeDetector and BuildManifest migration (PH2-021)."""

from core.change_detector import ChangeDetector
from models.build_manifest import BuildManifest


def test_compute_hashes():
    """Verify hash computations are deterministic and correct."""
    content1 = "print('hello')"
    content2 = "print('world')"

    hash1 = ChangeDetector.compute_content_hash(content1)
    hash2 = ChangeDetector.compute_content_hash(content2)

    assert hash1 != hash2
    assert len(hash1) == 64  # SHA-256 hex length

    # Deterministic repository hash
    file_hashes = {"main.py": hash1, "utils.py": hash2}
    repo_hash1 = ChangeDetector.compute_repository_hash(file_hashes)

    file_hashes_shuffled = {"utils.py": hash2, "main.py": hash1}
    repo_hash2 = ChangeDetector.compute_repository_hash(file_hashes_shuffled)

    assert repo_hash1 == repo_hash2


def test_first_build_detection():
    """Verify first build detects all files as added."""
    files = [
        {"path": "main.py", "content": "print('hello')"},
        {"path": "utils.py", "content": "import sys"},
    ]

    detector = ChangeDetector()
    change_set, file_hashes, repo_hash = detector.detect_changes(
        files, old_manifest=None
    )

    assert change_set.repository_changed is True
    assert change_set.added == {"main.py", "utils.py"}
    assert not change_set.modified
    assert not change_set.deleted
    assert not change_set.renamed
    assert not change_set.unchanged

    assert len(file_hashes) == 2
    assert repo_hash != ""


def test_no_change_detection():
    """Verify rebuild with no changes yields unchanged files."""
    files = [
        {"path": "main.py", "content": "print('hello')"},
        {"path": "utils.py", "content": "import sys"},
    ]

    detector = ChangeDetector()
    _, file_hashes, repo_hash = detector.detect_changes(files, old_manifest=None)

    manifest = BuildManifest(
        repository_hash=repo_hash,
        file_hashes=file_hashes,
        snapshot_versions={"symbols": 1},
    )

    # Detect again with manifest
    change_set, _, _ = detector.detect_changes(files, old_manifest=manifest)

    assert change_set.repository_changed is False
    assert not change_set.added
    assert not change_set.modified
    assert not change_set.deleted
    assert not change_set.renamed
    assert change_set.unchanged == {"main.py", "utils.py"}


def test_file_modifications():
    """Verify added, modified, and deleted files are detected correctly."""
    old_files = [
        {"path": "main.py", "content": "print('hello')"},
        {"path": "utils.py", "content": "import sys"},
        {"path": "old_file.py", "content": "class Old: pass"},
    ]

    detector = ChangeDetector()
    _, old_hashes, old_repo_hash = detector.detect_changes(old_files, old_manifest=None)

    manifest = BuildManifest(
        repository_hash=old_repo_hash,
        file_hashes=old_hashes,
    )

    # New state:
    # - main.py modified
    # - utils.py unchanged
    # - old_file.py deleted
    # - new_file.py added
    new_files = [
        {"path": "main.py", "content": "print('hello world')"},  # modified
        {"path": "utils.py", "content": "import sys"},  # unchanged
        {"path": "new_file.py", "content": "def new_func(): pass"},  # added
    ]

    change_set, _, _ = detector.detect_changes(new_files, old_manifest=manifest)

    assert change_set.repository_changed is True
    assert change_set.added == {"new_file.py"}
    assert change_set.modified == {"main.py"}
    assert change_set.deleted == {"old_file.py"}
    assert change_set.unchanged == {"utils.py"}
    assert not change_set.renamed


def test_rename_detection():
    """Verify file rename detection by content hash matching."""
    old_files = [
        {"path": "main.py", "content": "print('hello')"},
        {"path": "source.py", "content": "class ComplexLogic:\n    pass"},
    ]

    detector = ChangeDetector()
    _, old_hashes, old_repo_hash = detector.detect_changes(old_files, old_manifest=None)

    manifest = BuildManifest(
        repository_hash=old_repo_hash,
        file_hashes=old_hashes,
    )

    # rename source.py -> dest.py (contents remain identical)
    new_files = [
        {"path": "main.py", "content": "print('hello')"},
        {"path": "dest.py", "content": "class ComplexLogic:\n    pass"},
    ]

    change_set, _, _ = detector.detect_changes(new_files, old_manifest=manifest)

    assert change_set.repository_changed is True
    assert not change_set.added
    assert not change_set.deleted
    assert change_set.unchanged == {"main.py"}
    assert change_set.renamed == {"source.py": "dest.py"}


def test_manifest_migration():
    """Verify older BuildManifest dicts migrate automatically."""
    old_data = {
        "repository_hash": "abc123repo",
        "schema_version": 2,
        "embedding_schema": 4,
        "graph_schema": 5,
        "file_hashes": {"main.py": "hash123"},
    }

    manifest = BuildManifest.model_validate(old_data)

    assert manifest.repository_hash == "abc123repo"
    assert manifest.schema_versions == {"global": 2}
    assert manifest.embedding_schema_version == 4
    assert manifest.embedding_schema == 4
    assert manifest.graph_schema_version == 5
    assert manifest.graph_schema == 5
    assert manifest.application_version == "1.0.0"
    assert manifest.build_duration_ms == 0.0
