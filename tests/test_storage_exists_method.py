"""Tests for TodoStorage.exists() method.

This test suite verifies the file existence check functionality
for TodoStorage, providing a cleaner API than direct path access.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_before_save(tmp_path) -> None:
    """Test that exists() returns False when file has not been created."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # File should not exist initially
    assert storage.exists() is False


def test_exists_returns_true_after_save(tmp_path) -> None:
    """Test that exists() returns True after save() is called."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # File should not exist initially
    assert storage.exists() is False

    # Save some todos
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Now file should exist
    assert storage.exists() is True


def test_exists_reflects_external_file_deletion(tmp_path) -> None:
    """Test that exists() reflects state when file is deleted externally."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)
    assert storage.exists() is True

    # Delete file externally
    db.unlink()

    # exists() should now return False
    assert storage.exists() is False


def test_exists_with_custom_path(tmp_path) -> None:
    """Test exists() works with custom database path in subdirectory."""
    db = tmp_path / "subdir" / "todo.json"
    storage = TodoStorage(str(db))

    # Should not exist initially
    assert storage.exists() is False

    # Save creates parent directory and file
    storage.save([Todo(id=1, text="nested")])

    # Should exist now
    assert storage.exists() is True
