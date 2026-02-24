"""Tests for TodoStorage.exists() method (Issue #5483).

These tests verify that:
1. exists() returns False when no storage file exists
2. exists() returns True after save() has been called
3. exists() returns False if path exists but is a directory
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_before_save(tmp_path) -> None:
    """exists() should return False when no database file exists yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    assert storage.exists() is False


def test_exists_returns_true_after_save(tmp_path) -> None:
    """exists() should return True after save() has created the file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initially should not exist
    assert storage.exists() is False

    # Save some todos
    todos = [Todo(id=1, text="test task")]
    storage.save(todos)

    # Now should exist
    assert storage.exists() is True


def test_exists_returns_true_for_existing_valid_file(tmp_path) -> None:
    """exists() should return True for a pre-existing valid database file."""
    db = tmp_path / "existing.json"

    # Create a valid JSON file manually
    db.write_text('[{"id": 1, "text": "existing task", "done": false}]', encoding="utf-8")

    storage = TodoStorage(str(db))
    assert storage.exists() is True


def test_exists_returns_false_if_path_is_directory(tmp_path) -> None:
    """exists() should return False if the path points to a directory, not a file."""
    # Create a directory at the expected path
    dir_path = tmp_path / "todo.json"
    dir_path.mkdir()

    storage = TodoStorage(str(dir_path))
    # is_file() should return False for directories
    assert storage.exists() is False


def test_exists_uses_is_file_not_exists(tmp_path) -> None:
    """Verify that exists() checks is_file() not just path existence."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Should be False initially
    assert storage.exists() is False

    # After creating as a file, should be True
    db.touch()
    assert storage.exists() is True
