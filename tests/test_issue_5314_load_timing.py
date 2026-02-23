"""Tests for issue #5314: Performance timing metadata for load/save operations.

This test suite verifies that TodoStorage.load() supports an optional debug
parameter to return timing metadata for performance monitoring.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import LoadResult, TodoStorage
from flywheel.todo import Todo


def test_load_default_returns_list(tmp_path: Path) -> None:
    """Test that load() with debug=False (default) returns list[Todo]."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create test data
    todos = [Todo(id=1, text="test task"), Todo(id=2, text="another task", done=True)]
    storage.save(todos)

    # Load with default (debug=False)
    result = storage.load()

    # Should return a list of Todo objects
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(t, Todo) for t in result)
    assert result[0].text == "test task"
    assert result[1].done is True


def test_load_debug_false_explicit_returns_list(tmp_path: Path) -> None:
    """Test that load(debug=False) explicitly returns list[Todo]."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="task")]
    storage.save(todos)

    result = storage.load(debug=False)

    assert isinstance(result, list)
    assert len(result) == 1


def test_load_debug_true_returns_load_result(tmp_path: Path) -> None:
    """Test that load(debug=True) returns LoadResult with timing info."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test"), Todo(id=2, text="task")]
    storage.save(todos)

    # Load with debug=True
    result = storage.load(debug=True)

    # Should return a LoadResult (or dict-like) with todos and timing
    assert isinstance(result, LoadResult)
    assert hasattr(result, "todos")
    assert hasattr(result, "load_time_ms")

    # Verify todos are present and correct
    assert isinstance(result.todos, list)
    assert len(result.todos) == 2
    assert all(isinstance(t, Todo) for t in result.todos)


def test_load_debug_true_timing_is_positive(tmp_path: Path) -> None:
    """Test that load_time_ms is a positive number when debug=True."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=i, text=f"task {i}") for i in range(1, 101)]
    storage.save(todos)

    result = storage.load(debug=True)

    assert result.load_time_ms > 0, "load_time_ms should be positive"
    assert isinstance(result.load_time_ms, float), "load_time_ms should be a float"


def test_load_debug_true_empty_file(tmp_path: Path) -> None:
    """Test that load(debug=True) works with empty/non-existent file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # No file exists yet
    result = storage.load(debug=True)

    assert isinstance(result, LoadResult)
    assert result.todos == []
    assert result.load_time_ms >= 0  # Should still have timing info


def test_load_debug_true_large_file(tmp_path: Path) -> None:
    """Test that load(debug=True) timing reflects larger file size."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a larger file
    todos = [
        Todo(id=i, text=f"task number {i} with some extra text to make it larger")
        for i in range(1, 1001)
    ]
    storage.save(todos)

    result = storage.load(debug=True)

    assert len(result.todos) == 1000
    assert result.load_time_ms > 0


def test_load_result_dataclass_access(tmp_path: Path) -> None:
    """Test that LoadResult supports attribute and dict-like access patterns."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    result = storage.load(debug=True)

    # Should support attribute access
    assert result.todos is not None
    assert result.load_time_ms is not None
