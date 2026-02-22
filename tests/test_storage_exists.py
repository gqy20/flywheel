"""Tests for TodoStorage.exists() method.

This test suite verifies that TodoStorage provides a simple exists() method
to check if the storage file exists, addressing issue #5192.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_when_file_does_not_exist(tmp_path) -> None:
    """Test that exists() returns False when storage file has not been created."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # File should not exist yet
    assert not db.exists()
    # exists() should return False
    assert storage.exists() is False


def test_exists_returns_true_when_file_exists(tmp_path) -> None:
    """Test that exists() returns True after save() creates the file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save creates the file
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # File should now exist
    assert db.exists()
    # exists() should return True
    assert storage.exists() is True


def test_exists_with_default_path() -> None:
    """Test that exists() works with default path (no path argument)."""
    storage = TodoStorage()

    # Default path is .todo.json in current directory
    # Just verify the method exists and returns a bool
    result = storage.exists()
    assert isinstance(result, bool)


def test_exists_after_multiple_operations(tmp_path) -> None:
    """Test exists() reflects file state across multiple save/load operations."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initially doesn't exist
    assert storage.exists() is False

    # After first save, exists
    storage.save([Todo(id=1, text="first")])
    assert storage.exists() is True

    # After loading, still exists (file not deleted)
    loaded = storage.load()
    assert len(loaded) == 1
    assert storage.exists() is True

    # After another save, still exists
    storage.save([Todo(id=1, text="updated"), Todo(id=2, text="new")])
    assert storage.exists() is True
