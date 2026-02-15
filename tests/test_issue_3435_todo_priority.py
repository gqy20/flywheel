"""Tests for Todo priority field (Issue #3435).

These tests verify that:
1. Todo dataclass includes priority field with default value
2. Todo.set_priority() validates and updates priority with timestamp
3. Todo.from_dict() accepts optional 'priority' key
4. Todo.to_dict() includes priority in output
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoPriorityField:
    """Tests for the priority field on Todo dataclass."""

    def test_todo_has_priority_field_with_default(self) -> None:
        """Todo should have a priority field with a sensible default value."""
        todo = Todo(id=1, text="buy milk")
        assert hasattr(todo, "priority")
        # Default priority should be 2 (medium/normal priority)
        assert todo.priority == 2

    def test_todo_can_be_created_with_priority(self) -> None:
        """Todo can be created with an explicit priority value."""
        todo = Todo(id=1, text="urgent task", priority=1)
        assert todo.priority == 1

        todo2 = Todo(id=2, text="low priority task", priority=3)
        assert todo2.priority == 3

    def test_set_priority_updates_field(self) -> None:
        """set_priority() should update the priority field."""
        todo = Todo(id=1, text="task", priority=2)
        original_updated_at = todo.updated_at

        todo.set_priority(1)

        assert todo.priority == 1
        assert todo.updated_at != original_updated_at

    def test_set_priority_validates_range(self) -> None:
        """set_priority() should only accept values 1, 2, or 3."""
        todo = Todo(id=1, text="task")

        # Valid values should work
        todo.set_priority(1)
        assert todo.priority == 1

        todo.set_priority(2)
        assert todo.priority == 2

        todo.set_priority(3)
        assert todo.priority == 3

    def test_set_priority_rejects_invalid_values(self) -> None:
        """set_priority() should raise ValueError for invalid priority."""
        todo = Todo(id=1, text="task")

        # Priority 0 should be invalid
        try:
            todo.set_priority(0)
            raise AssertionError("Expected ValueError for priority 0")
        except ValueError as e:
            assert "priority" in str(e).lower()

        # Priority 4 should be invalid
        try:
            todo.set_priority(4)
            raise AssertionError("Expected ValueError for priority 4")
        except ValueError as e:
            assert "priority" in str(e).lower()

        # Negative priority should be invalid
        try:
            todo.set_priority(-1)
            raise AssertionError("Expected ValueError for priority -1")
        except ValueError as e:
            assert "priority" in str(e).lower()

    def test_to_dict_includes_priority(self) -> None:
        """to_dict() should include the priority field in output."""
        todo = Todo(id=1, text="task", priority=1)
        result = todo.to_dict()

        assert "priority" in result
        assert result["priority"] == 1

    def test_to_dict_includes_default_priority(self) -> None:
        """to_dict() should include priority even with default value."""
        todo = Todo(id=1, text="task")
        result = todo.to_dict()

        assert "priority" in result
        assert result["priority"] == 2  # default

    def test_from_dict_accepts_priority(self) -> None:
        """from_dict() should accept an optional 'priority' key."""
        data = {"id": 1, "text": "task", "priority": 3}
        todo = Todo.from_dict(data)

        assert todo.priority == 3

    def test_from_dict_uses_default_priority_when_missing(self) -> None:
        """from_dict() should use default priority when key is missing."""
        data = {"id": 1, "text": "task"}
        todo = Todo.from_dict(data)

        assert todo.priority == 2  # default

    def test_from_dict_validates_priority(self) -> None:
        """from_dict() should validate priority values."""
        # Invalid priority should raise ValueError
        try:
            Todo.from_dict({"id": 1, "text": "task", "priority": 5})
            raise AssertionError("Expected ValueError for invalid priority")
        except ValueError as e:
            assert "priority" in str(e).lower()

    def test_roundtrip_to_dict_from_dict_preserves_priority(self) -> None:
        """Priority should survive a roundtrip through to_dict/from_dict."""
        original = Todo(id=1, text="task", priority=1)
        data = original.to_dict()
        restored = Todo.from_dict(data)

        assert restored.priority == original.priority == 1
