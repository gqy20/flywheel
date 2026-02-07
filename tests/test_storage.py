"""Tests for TodoStorage."""

from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestTodoStoragePathTraversal:
    """Test path traversal vulnerability fix."""

    def test_path_with_double_dot_rejected(self, tmp_path):
        """Paths with '..' components should raise ValueError."""
        with pytest.raises(ValueError, match="path traversal"):
            TodoStorage("../../../etc/passwd")

    def test_path_with_double_dot_rejected_variant(self, tmp_path):
        """Paths with '..' components in middle should raise ValueError."""
        with pytest.raises(ValueError, match="path traversal"):
            TodoStorage("subdir/../../etc/passwd")

    def test_path_with_double_dot_rejected_windows(self, tmp_path):
        """Paths with '..' components (Windows style) should raise ValueError."""
        with pytest.raises(ValueError, match="path traversal"):
            TodoStorage("..\\..\\system32\\config")

    def test_normal_paths_allowed(self, tmp_path):
        """Normal relative paths should work fine."""
        # Test current directory default
        storage1 = TodoStorage()
        assert storage1.path == Path(".todo.json")

        # Test simple filename
        storage2 = TodoStorage("custom.json")
        assert storage2.path == Path("custom.json")

        # Test subdirectory (no ..)
        storage3 = TodoStorage("data/todos.json")
        assert storage3.path == Path("data/todos.json")

    def test_absolute_paths_allowed(self, tmp_path):
        """Absolute paths should work fine (user-controlled location)."""
        abs_path = tmp_path / "todos.json"
        storage = TodoStorage(str(abs_path))
        assert storage.path == abs_path


class TestTodoStorage:
    """Test TodoStorage functionality."""

    def test_load_empty(self, tmp_path):
        """Empty storage returns empty list."""
        storage = TodoStorage(str(tmp_path / "empty.json"))
        assert storage.load() == []

    def test_save_and_load(self, tmp_path):
        """Save and load todos roundtrip."""
        db_path = tmp_path / "test.json"
        storage = TodoStorage(str(db_path))

        todos = [Todo(id=1, text="Buy milk"), Todo(id=2, text="Write code")]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].id == 1
        assert loaded[0].text == "Buy milk"
        assert loaded[1].id == 2
        assert loaded[1].text == "Write code"

    def test_invalid_json_raises(self, tmp_path):
        """Invalid JSON raises ValueError."""
        db_path = tmp_path / "invalid.json"
        db_path.write_text("not json")

        storage = TodoStorage(str(db_path))
        with pytest.raises(ValueError):
            storage.load()

    def test_next_id_empty(self):
        """Empty todo list returns id 1."""
        storage = TodoStorage()
        assert storage.next_id([]) == 1

    def test_next_id_existing(self):
        """Existing todos return max + 1."""
        storage = TodoStorage()
        todos = [Todo(id=1, text="First"), Todo(id=3, text="Third")]
        assert storage.next_id(todos) == 4
