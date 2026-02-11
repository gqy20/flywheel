"""Tests for issue #2779: load() return statistics metadata.

This test suite verifies that TodoStorage.load() returns metadata including:
- todo count
- file size
- load time
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage, StorageLoadResult
from flywheel.todo import Todo


class TestStorageLoadResult:
    """Test StorageLoadResult dataclass."""

    def test_storage_load_result_attributes(self) -> None:
        """Test StorageLoadResult has required attributes."""
        todos = [Todo(id=1, text="test")]
        result = StorageLoadResult(todos=todos, file_size=1024, load_time_ms=50.0)

        assert result.todos == todos
        assert result.file_size == 1024
        assert result.load_time_ms == 50.0
        assert result.todo_count == 1


class TestLoadStatistics:
    """Test load() returns statistics metadata."""

    def test_load_returns_storage_load_result(self, tmp_path) -> None:
        """Test that load() returns StorageLoadResult with todos and metadata."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial todos
        todos = [
            Todo(id=1, text="first todo"),
            Todo(id=2, text="second todo"),
            Todo(id=3, text="third todo", done=True),
        ]
        storage.save(todos)

        # Load and verify return type
        result = storage.load()
        assert isinstance(result, StorageLoadResult)

        # Verify todos are loaded correctly
        assert len(result.todos) == 3
        assert result.todos[0].text == "first todo"
        assert result.todos[1].text == "second todo"
        assert result.todos[2].done is True

    def test_load_todo_count(self, tmp_path) -> None:
        """Test that load() returns correct todo count."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Empty file
        result = storage.load()
        assert result.todo_count == 0
        assert result.todos == []

        # Add some todos
        todos = [Todo(id=i, text=f"todo {i}") for i in range(1, 6)]
        storage.save(todos)

        result = storage.load()
        assert result.todo_count == 5
        assert result.todos == result.todos  # Verify consistency

    def test_load_file_size(self, tmp_path) -> None:
        """Test that load() returns correct file size in bytes."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create todos
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        result = storage.load()
        expected_size = db.stat().st_size
        assert result.file_size == expected_size
        assert result.file_size > 0

    def test_load_time_measurement(self, tmp_path) -> None:
        """Test that load() measures load time in milliseconds."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create todos
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

        # Load and measure time
        result = storage.load()
        assert isinstance(result.load_time_ms, float)
        assert result.load_time_ms >= 0

        # Load should be fast for small file
        assert result.load_time_ms < 1000  # Less than 1 second

    def test_load_empty_file_returns_empty_result(self, tmp_path) -> None:
        """Test that loading non-existent file returns empty result."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        result = storage.load()
        assert isinstance(result, StorageLoadResult)
        assert result.todo_count == 0
        assert result.todos == []
        assert result.file_size == 0
        # load_time_ms should still be measured
        assert isinstance(result.load_time_ms, float)


class TestLoadSimpleBackwardCompatibility:
    """Test load_simple() maintains backward compatibility."""

    def test_load_simple_returns_list_of_todos(self, tmp_path) -> None:
        """Test that load_simple() returns list[Todo] for backward compatibility."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create todos
        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        # load_simple should return list[Todo]
        result = storage.load_simple()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].text == "test"

    def test_load_simple_nonexistent_returns_empty_list(self, tmp_path) -> None:
        """Test that load_simple() returns empty list for non-existent file."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        result = storage.load_simple()
        assert result == []
