"""Tests for Todo priority field support (Issue #3980)."""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoPriorityField:
    """Tests for the priority field in Todo dataclass."""

    def test_todo_with_priority_creates_correctly(self) -> None:
        """Todo should accept priority field with specified value."""
        todo = Todo(id=1, text="a", priority=3)
        assert todo.priority == 3

    def test_todo_priority_defaults_to_zero(self) -> None:
        """Todo priority should default to 0 when not specified."""
        todo = Todo(id=1, text="a")
        assert todo.priority == 0

    def test_from_dict_with_priority_returns_correct_value(self) -> None:
        """from_dict() should correctly parse priority field."""
        todo = Todo.from_dict({"id": 1, "text": "a", "priority": 2})
        assert todo.priority == 2

    def test_from_dict_without_priority_defaults_to_zero(self) -> None:
        """from_dict() should return priority=0 when field is missing."""
        todo = Todo.from_dict({"id": 1, "text": "a"})
        assert todo.priority == 0

    def test_to_dict_includes_priority(self) -> None:
        """to_dict() output should include priority field."""
        todo = Todo(id=1, text="a", priority=3)
        data = todo.to_dict()
        assert "priority" in data
        assert data["priority"] == 3

    def test_to_dict_includes_priority_with_default(self) -> None:
        """to_dict() output should include priority field even with default value."""
        todo = Todo(id=1, text="a")
        data = todo.to_dict()
        assert "priority" in data
        assert data["priority"] == 0

    def test_storage_roundtrip_with_priority(self, tmp_path) -> None:
        """Todo with priority should roundtrip through storage."""
        from flywheel.storage import TodoStorage

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [Todo(id=1, text="high", priority=3), Todo(id=2, text="low", priority=0)]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].priority == 3
        assert loaded[1].priority == 0
