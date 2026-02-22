"""Tests for issue #5192: Add exists() method to TodoStorage.

This test suite verifies that TodoStorage.exists() provides a clean API
for checking if the storage file exists, without exposing internal path details.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_when_file_does_not_exist(tmp_path) -> None:
    """Test that exists() returns False when storage file doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    assert storage.exists() is False


def test_exists_returns_true_when_file_exists(tmp_path) -> None:
    """Test that exists() returns True when storage file exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create the file manually
    db.write_text("[]", encoding="utf-8")

    assert storage.exists() is True


def test_exists_returns_true_after_save(tmp_path) -> None:
    """Test that exists() returns True after save() creates the file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initially should not exist
    assert storage.exists() is False

    # After saving, should exist
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    assert storage.exists() is True


def test_exists_returns_false_for_empty_path(tmp_path) -> None:
    """Test that exists() returns False when path is effectively empty or invalid."""
    # Create storage with default path that doesn't exist
    # Using a non-existent subdirectory to ensure it doesn't exist
    non_existent = tmp_path / "nonexistent_dir" / ".todo.json"
    storage = TodoStorage(str(non_existent))

    assert storage.exists() is False


def test_exists_has_type_annotation(tmp_path) -> None:
    """Test that exists() method has proper type annotation returning bool."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Verify the method returns a bool
    result = storage.exists()
    assert isinstance(result, bool)


def test_exists_works_after_file_deleted(tmp_path) -> None:
    """Test that exists() correctly reflects state after file is deleted."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save
    todos = [Todo(id=1, text="test")]
    storage.save(todos)
    assert storage.exists() is True

    # Delete the file externally
    db.unlink()

    # Should now return False
    assert storage.exists() is False
