"""Tests for issue #2779: load() return statistics metadata.

This test suite verifies that TodoStorage.load_with_stats() returns
a dataclass containing todos list plus metadata:
- file_size: Size of the JSON file in bytes
- load_time_ms: Time taken to load the file in milliseconds
- todo_count: Number of todos loaded

The enhancement is non-breaking: adds load_with_stats() method while
keeping existing load() unchanged.
"""

from __future__ import annotations

from flywheel.storage import StorageLoadResult, TodoStorage
from flywheel.todo import Todo


def test_load_with_stats_returns_dataclass_with_all_fields(tmp_path) -> None:
    """Test that load_with_stats returns StorageLoadResult with all required fields."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create test data
    todos = [
        Todo(id=1, text="task 1"),
        Todo(id=2, text="task 2"),
        Todo(id=3, text="task 3"),
    ]
    storage.save(todos)

    # Call load_with_stats
    result = storage.load_with_stats()

    # Verify result is StorageLoadResult dataclass
    assert isinstance(result, StorageLoadResult)

    # Verify all required fields are present
    assert hasattr(result, "todos")
    assert hasattr(result, "file_size")
    assert hasattr(result, "load_time_ms")
    assert hasattr(result, "todo_count")


def test_load_with_stats_contains_correct_todos(tmp_path) -> None:
    """Test that load_with_stats returns correct todos list."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    original_todos = [
        Todo(id=1, text="first task", done=False),
        Todo(id=2, text="second task", done=True),
    ]
    storage.save(original_todos)

    result = storage.load_with_stats()

    assert len(result.todos) == 2
    assert result.todos[0].id == 1
    assert result.todos[0].text == "first task"
    assert result.todos[0].done is False
    assert result.todos[1].id == 2
    assert result.todos[1].text == "second task"
    assert result.todos[1].done is True


def test_load_with_stats_returns_correct_file_size(tmp_path) -> None:
    """Test that load_with_stats returns accurate file_size."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    result = storage.load_with_stats()

    # Verify file_size matches actual file size
    actual_size = db.stat().st_size
    assert result.file_size == actual_size
    assert result.file_size > 0


def test_load_with_stats_returns_correct_todo_count(tmp_path) -> None:
    """Test that load_with_stats returns correct todo_count."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Test with empty storage
    result = storage.load_with_stats()
    assert result.todo_count == 0
    assert result.todos == []

    # Test with 1 todo
    storage.save([Todo(id=1, text="single")])
    result = storage.load_with_stats()
    assert result.todo_count == 1

    # Test with multiple todos
    storage.save([
        Todo(id=1, text="task 1"),
        Todo(id=2, text="task 2"),
        Todo(id=3, text="task 3"),
    ])
    result = storage.load_with_stats()
    assert result.todo_count == 3


def test_load_with_stats_tracks_load_time(tmp_path) -> None:
    """Test that load_with_stats measures and returns load_time_ms."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="timed task")]
    storage.save(todos)

    result = storage.load_with_stats()

    # Verify load_time_ms is a non-negative number
    assert isinstance(result.load_time_ms, float)
    assert result.load_time_ms >= 0


def test_load_with_stats_on_nonexistent_file(tmp_path) -> None:
    """Test that load_with_stats handles non-existent file correctly."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    result = storage.load_with_stats()

    # Should return empty result
    assert result.todos == []
    assert result.todo_count == 0
    assert result.file_size == 0
    assert result.load_time_ms >= 0


def test_original_load_unchanged_for_backward_compatibility(tmp_path) -> None:
    """Test that original load() method still returns list[Todo] unchanged."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    original_todos = [
        Todo(id=1, text="backward compat test"),
        Todo(id=2, text="another task"),
    ]
    storage.save(original_todos)

    # Original load() should still return list[Todo]
    result = storage.load()

    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], Todo)
    assert result[0].text == "backward compat test"


def test_file_size_matches_large_file(tmp_path) -> None:
    """Test file_size accuracy with larger content."""
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a larger file with many todos
    todos = [Todo(id=i, text=f"task {i} with some content") for i in range(100)]
    storage.save(todos)

    result = storage.load_with_stats()

    # Verify file_size is accurate
    actual_size = db.stat().st_size
    assert result.file_size == actual_size
    assert result.todo_count == 100
