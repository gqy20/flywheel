"""Tests for TodoStorage.exists() method.

This test suite verifies that TodoStorage.exists() provides a simple,
O(1) way to check if the database file exists without loading it.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_before_any_save(tmp_path) -> None:
    """Test that exists() returns False when no database file has been created."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Before any save, file should not exist
    assert storage.exists() is False


def test_exists_returns_true_after_save(tmp_path) -> None:
    """Test that exists() returns True after save() creates the file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # After save, file should exist
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    assert storage.exists() is True


def test_exists_returns_false_for_nonexistent_path() -> None:
    """Test that exists() returns False for a path that doesn't exist."""
    storage = TodoStorage("/nonexistent/path/to/todo.json")

    assert storage.exists() is False


def test_exists_returns_true_for_existing_file(tmp_path) -> None:
    """Test that exists() returns True for a pre-existing valid database file."""
    db = tmp_path / "existing.json"
    # Create a valid JSON file manually
    db.write_text('[]', encoding="utf-8")

    storage = TodoStorage(str(db))

    assert storage.exists() is True
