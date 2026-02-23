"""Tests for issue #5314: Performance timing metadata in load().

This test suite verifies that TodoStorage.load() supports an optional
debug parameter that returns performance timing information.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_without_debug_returns_list(tmp_path: Path) -> None:
    """Test that load() without debug parameter returns list[Todo] (default behavior)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save some todos
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Load without debug parameter
    result = storage.load()

    # Should return a list of Todo objects (backward compatible)
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], Todo)
    assert result[0].text == "test todo"


def test_load_with_debug_false_returns_list(tmp_path: Path) -> None:
    """Test that load(debug=False) returns list[Todo] (backward compatible)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save some todos
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Load with debug=False
    result = storage.load(debug=False)

    # Should return a list of Todo objects
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], Todo)


def test_load_with_debug_true_returns_dict_with_timing(tmp_path: Path) -> None:
    """Test that load(debug=True) returns dict with todos and load_time_ms."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save some todos
    todos = [Todo(id=1, text="test todo"), Todo(id=2, text="another todo")]
    storage.save(todos)

    # Load with debug=True
    result = storage.load(debug=True)

    # Should return a dict with todos and timing info
    assert isinstance(result, dict)
    assert "todos" in result
    assert "load_time_ms" in result

    # Check todos
    assert isinstance(result["todos"], list)
    assert len(result["todos"]) == 2
    assert isinstance(result["todos"][0], Todo)
    assert result["todos"][0].text == "test todo"

    # Check load_time_ms is a positive number
    assert isinstance(result["load_time_ms"], float)
    assert result["load_time_ms"] >= 0


def test_load_with_debug_true_load_time_ms_is_positive(tmp_path: Path) -> None:
    """Test that load_time_ms is a positive number."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save some todos
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Load with debug=True
    result = storage.load(debug=True)

    # load_time_ms should be >= 0 (can be 0 for very fast operations)
    assert result["load_time_ms"] >= 0


def test_load_with_debug_true_on_empty_file(tmp_path: Path) -> None:
    """Test that load(debug=True) works correctly on empty/missing file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # No file exists, load should return empty result
    result = storage.load(debug=True)

    assert isinstance(result, dict)
    assert "todos" in result
    assert "load_time_ms" in result
    assert result["todos"] == []
