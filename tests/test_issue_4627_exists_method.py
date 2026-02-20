"""Tests for issue #4627: exists() method for checking storage file existence.

This test suite verifies that TodoStorage.exists() provides an efficient way
to check if the storage file exists without loading and parsing the entire JSON.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_exists_returns_false_when_file_does_not_exist(tmp_path) -> None:
    """Test that exists() returns False when the storage file does not exist."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    assert storage.exists() is False


def test_exists_returns_true_when_file_exists(tmp_path) -> None:
    """Test that exists() returns True when the storage file exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file by saving some todos
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    assert storage.exists() is True


def test_exists_returns_correct_value_equivalent_to_path_exists(tmp_path) -> None:
    """Test that exists() return value is equivalent to Path.exists() result."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Before file exists
    assert storage.exists() == db.exists()
    assert storage.exists() is False

    # After file exists
    storage.save([Todo(id=1, text="test")])
    assert storage.exists() == db.exists()
    assert storage.exists() is True


def test_exists_method_has_docstring() -> None:
    """Test that exists() method has a docstring."""
    assert TodoStorage.exists.__doc__ is not None
    assert len(TodoStorage.exists.__doc__) > 0


def test_exists_returns_bool_type() -> None:
    """Test that exists() returns bool type as per acceptance criteria."""
    storage = TodoStorage("/nonexistent/path/todo.json")
    result = storage.exists()

    assert isinstance(result, bool)
