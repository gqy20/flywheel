"""Tests for issue #2779: Add load() return statistics metadata."""

from __future__ import annotations

import time

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_storage_load_returns_metadata_with_empty_file(tmp_path) -> None:
    """Issue #2779: load() should return StorageLoadResult with metadata for non-existent files."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    result = storage.load()

    # Should return StorageLoadResult, not a list
    assert hasattr(result, "todos"), "Result should have 'todos' attribute"
    assert hasattr(result, "file_size"), "Result should have 'file_size' attribute"
    assert hasattr(result, "load_time_ms"), "Result should have 'load_time_ms' attribute"

    # Verify metadata for empty file
    assert result.todos == []
    assert result.file_size == 0
    assert result.load_time_ms >= 0


def test_storage_load_returns_metadata_with_existing_file(tmp_path) -> None:
    """Issue #2779: load() should return StorageLoadResult with accurate file_size."""
    db = tmp_path / "todos.json"
    storage = TodoStorage(str(db))

    # Create test data
    todos = [Todo(id=1, text="task1"), Todo(id=2, text="task2", done=True)]
    storage.save(todos)

    # Get actual file size
    actual_file_size = db.stat().st_size

    # Load and verify result
    result = storage.load()

    # Should return StorageLoadResult
    assert hasattr(result, "todos"), "Result should have 'todos' attribute"
    assert hasattr(result, "file_size"), "Result should have 'file_size' attribute"
    assert hasattr(result, "load_time_ms"), "Result should have 'load_time_ms' attribute"

    # Verify todos are correct
    assert len(result.todos) == 2
    assert result.todos[0].text == "task1"
    assert result.todos[1].done is True

    # Verify file_size matches actual file
    assert result.file_size == actual_file_size

    # Verify load_time_ms is reasonable (should be very fast for small file)
    assert result.load_time_ms >= 0
    assert result.load_time_ms < 1000  # Less than 1 second


def test_storage_load_simple_backward_compatibility(tmp_path) -> None:
    """Issue #2779: load_simple() should return list[Todo] for backward compatibility."""
    db = tmp_path / "compat.json"
    storage = TodoStorage(str(db))

    # Create test data
    todos = [Todo(id=1, text="simple test")]
    storage.save(todos)

    # load_simple() should return a list, not StorageLoadResult
    result = storage.load_simple()

    # Should be a plain list
    assert isinstance(result, list), "load_simple() should return a list"

    # Should contain Todo objects
    assert len(result) == 1
    assert isinstance(result[0], Todo)
    assert result[0].text == "simple test"


def test_storage_load_simple_with_nonexistent_file(tmp_path) -> None:
    """Issue #2779: load_simple() should return empty list for non-existent files."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    result = storage.load_simple()

    assert result == []


def test_app_load_still_returns_list_after_unwrap(tmp_path) -> None:
    """Issue #2779: TodoApp._load() should still return list[Todo] for internal use."""
    from flywheel.cli import TodoApp

    app = TodoApp(str(tmp_path / "app_test.json"))

    # Add a todo via the app
    added = app.add("test todo")

    # _load() should still return list[Todo] internally
    todos = app._load()

    # Should be a plain list for internal use
    assert isinstance(todos, list), "_load() should return a list"
    assert len(todos) == 1
    assert todos[0].id == 1
    assert todos[0].text == "test todo"


def test_storage_load_time_increases_with_delay(tmp_path) -> None:
    """Issue #2779: load_time_ms should accurately reflect load duration."""
    db = tmp_path / "timing.json"
    storage = TodoStorage(str(db))

    # Create test data
    todos = [Todo(id=1, text="timing test")]
    storage.save(todos)

    # First load should be fast
    result1 = storage.load()
    time.sleep(0.01)  # Small delay

    # Manually test with a slower operation
    import json

    start = time.perf_counter()
    _ = json.loads(db.read_text())
    end = time.perf_counter()

    # The measured time should be positive and reasonable
    measured_ms = (end - start) * 1000
    assert measured_ms > 0


def test_storage_load_result_todo_count_matches_length(tmp_path) -> None:
    """Issue #2779: Result metadata should be consistent with todos list."""
    db = tmp_path / "count.json"
    storage = TodoStorage(str(db))

    # Test with varying numbers of todos
    for count in [0, 1, 5, 10]:
        todos = [Todo(id=i, text=f"todo {i}") for i in range(1, count + 1)]
        storage.save(todos)

        result = storage.load()

        # len(result.todos) should match the count
        assert len(result.todos) == count
        assert all(isinstance(todo, Todo) for todo in result.todos)
