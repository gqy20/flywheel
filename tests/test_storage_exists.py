"""Tests for TodoStorage.exists() method.

This test suite verifies the exists() method which checks if the storage
file exists without loading it.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_when_file_does_not_exist(tmp_path) -> None:
    """Test that exists() returns False when the storage file doesn't exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # File should not exist initially
    assert not db.exists()
    assert storage.exists() is False


def test_exists_returns_true_after_save(tmp_path) -> None:
    """Test that exists() returns True after save() creates the file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initially doesn't exist
    assert storage.exists() is False

    # Save creates the file
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Now it should exist
    assert db.exists()
    assert storage.exists() is True


def test_exists_returns_bool_type(tmp_path) -> None:
    """Test that exists() returns a bool type."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Check return type when file doesn't exist
    result = storage.exists()
    assert isinstance(result, bool)
    assert result is False

    # Check return type when file exists
    storage.save([Todo(id=1, text="test")])
    result = storage.exists()
    assert isinstance(result, bool)
    assert result is True


def test_exists_after_file_deletion(tmp_path) -> None:
    """Test that exists() correctly reflects file state after deletion."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save
    storage.save([Todo(id=1, text="test")])
    assert storage.exists() is True

    # Delete file
    db.unlink()

    # Should reflect the deletion
    assert storage.exists() is False
