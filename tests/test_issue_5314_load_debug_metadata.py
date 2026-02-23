"""Tests for load() debug parameter with performance timing metadata.

Issue #5314: Add performance timing metadata to load/save operations.

Acceptance criteria:
- load() method accepts optional debug parameter
- debug=True returns a dict with todos and load_time_ms fields
- debug=False (default) behavior unchanged - returns list[Todo]
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestLoadDebugParameter:
    """Tests for load() debug parameter functionality."""

    def test_load_default_returns_list_of_todos(self, tmp_path: Path) -> None:
        """Test that default behavior (debug=False) returns list[Todo]."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create test data
        todos = [Todo(id=1, text="test"), Todo(id=2, text="another")]
        storage.save(todos)

        # Default load should return list[Todo]
        loaded = storage.load()
        assert isinstance(loaded, list)
        assert len(loaded) == 2
        assert all(isinstance(t, Todo) for t in loaded)

    def test_load_explicit_debug_false_returns_list(self, tmp_path: Path) -> None:
        """Test that explicit debug=False returns list[Todo]."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        loaded = storage.load(debug=False)
        assert isinstance(loaded, list)
        assert len(loaded) == 1
        assert isinstance(loaded[0], Todo)

    def test_load_debug_true_returns_dict_with_todos(self, tmp_path: Path) -> None:
        """Test that debug=True returns dict with 'todos' key."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test"), Todo(id=2, text="second")]
        storage.save(todos)

        result = storage.load(debug=True)
        assert isinstance(result, dict)
        assert "todos" in result
        assert isinstance(result["todos"], list)
        assert len(result["todos"]) == 2
        assert all(isinstance(t, Todo) for t in result["todos"])

    def test_load_debug_true_returns_load_time_ms(self, tmp_path: Path) -> None:
        """Test that debug=True returns dict with 'load_time_ms' key."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        result = storage.load(debug=True)
        assert "load_time_ms" in result
        assert isinstance(result["load_time_ms"], (int, float))

    def test_load_debug_true_load_time_ms_is_positive(self, tmp_path: Path) -> None:
        """Test that load_time_ms is a non-negative number."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="test")]
        storage.save(todos)

        result = storage.load(debug=True)
        assert result["load_time_ms"] >= 0

    def test_load_debug_true_empty_file(self, tmp_path: Path) -> None:
        """Test debug=True behavior when file doesn't exist."""
        db = tmp_path / "nonexistent.json"
        storage = TodoStorage(str(db))

        result = storage.load(debug=True)
        assert isinstance(result, dict)
        assert "todos" in result
        assert result["todos"] == []
        assert "load_time_ms" in result
        assert result["load_time_ms"] >= 0

    def test_load_debug_true_preserves_todo_data(self, tmp_path: Path) -> None:
        """Test that todos data is correctly preserved in debug mode."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        original_todos = [
            Todo(id=1, text="first task"),
            Todo(id=2, text="second task", done=True),
            Todo(id=3, text="unicode: 你好世界"),
        ]
        storage.save(original_todos)

        result = storage.load(debug=True)
        loaded_todos = result["todos"]

        assert len(loaded_todos) == 3
        assert loaded_todos[0].id == 1
        assert loaded_todos[0].text == "first task"
        assert loaded_todos[1].done is True
        assert loaded_todos[2].text == "unicode: 你好世界"
