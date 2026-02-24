"""Tests for TodoStorage.exists() method.

This test suite verifies that TodoStorage.exists() correctly reports
whether the database file exists, allowing callers to check initialization
status without triggering load operations.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_when_file_does_not_exist(tmp_path) -> None:
    """Test that exists() returns False when database file doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    assert storage.exists() is False


def test_exists_returns_true_when_file_exists(tmp_path) -> None:
    """Test that exists() returns True after database file is created."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initially doesn't exist
    assert storage.exists() is False

    # Save some todos to create the file
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Now it should exist
    assert storage.exists() is True


def test_exists_reflects_file_deletion(tmp_path) -> None:
    """Test that exists() reflects the actual file state after deletion."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create the file
    storage.save([Todo(id=1, text="test")])
    assert storage.exists() is True

    # Delete the file externally
    Path(db).unlink()

    # exists() should now return False
    assert storage.exists() is False


def test_exists_with_custom_path(tmp_path) -> None:
    """Test that exists() works with custom database paths."""
    custom_db = tmp_path / "custom" / "database.json"
    storage = TodoStorage(str(custom_db))

    # Initially doesn't exist (parent dir doesn't exist either)
    assert storage.exists() is False

    # Save creates the file and parent directory
    storage.save([Todo(id=1, text="custom path test")])
    assert storage.exists() is True
