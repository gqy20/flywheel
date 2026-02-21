"""Tests for TodoStorage.exists() helper method.

Regression test for issue #4975: Add file existence check helper method.

This test suite verifies that TodoStorage.exists() provides a convenient
way to check if the database file exists without requiring callers to
access the internal .path attribute.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_before_any_save(tmp_path) -> None:
    """Test exists() returns False when database file doesn't exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Before any save, file should not exist
    assert storage.exists() is False


def test_exists_returns_true_after_save(tmp_path) -> None:
    """Test exists() returns True after database file is created."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save some todos
    todos = [Todo(id=1, text="test task")]
    storage.save(todos)

    # After save, file should exist
    assert storage.exists() is True


def test_exists_returns_false_after_file_deleted(tmp_path) -> None:
    """Test exists() returns False if database file is deleted."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save todos
    todos = [Todo(id=1, text="test task")]
    storage.save(todos)
    assert storage.exists() is True

    # Delete the file externally
    db.unlink()

    # exists() should reflect the deletion
    assert storage.exists() is False


def test_exists_uses_internal_path_attribute(tmp_path) -> None:
    """Test that exists() correctly uses the storage's path."""
    custom_path = tmp_path / "custom" / "database.json"
    storage = TodoStorage(str(custom_path))

    # Initially doesn't exist
    assert storage.exists() is False

    # Save creates the file (and parent directory)
    storage.save([Todo(id=1, text="test")])

    # Now it exists
    assert storage.exists() is True


def test_exists_with_default_path() -> None:
    """Test exists() works with the default path."""
    storage = TodoStorage()  # Uses default .todo.json

    # The result depends on whether .todo.json exists in current directory
    # Just verify the method returns a boolean
    result = storage.exists()
    assert isinstance(result, bool)
