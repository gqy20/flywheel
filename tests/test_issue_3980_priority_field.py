"""Tests for Todo priority field (Issue #3980).

These tests verify that:
1. Todo dataclass has priority: int field with default 0
2. from_dict() correctly parses priority from data, defaulting to 0 when missing
3. to_dict() includes priority in output
4. Backward compatibility is maintained
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoPriorityField:
    """Test suite for Todo priority field functionality."""

    def test_todo_with_priority_created_correctly(self) -> None:
        """Todo can be created with explicit priority value."""
        todo = Todo(id=1, text="high priority task", priority=3)
        assert todo.priority == 3

    def test_todo_defaults_priority_to_zero(self) -> None:
        """Todo without priority should default to 0."""
        todo = Todo(id=1, text="normal task")
        assert todo.priority == 0

    def test_from_dict_parses_priority(self) -> None:
        """from_dict() should correctly parse priority field."""
        todo = Todo.from_dict({"id": 1, "text": "task", "priority": 2})
        assert todo.priority == 2

    def test_from_dict_defaults_missing_priority_to_zero(self) -> None:
        """from_dict() should default priority to 0 when missing (backward compat)."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.priority == 0

    def test_to_dict_includes_priority(self) -> None:
        """to_dict() should include priority in output."""
        todo = Todo(id=1, text="task", priority=5)
        result = todo.to_dict()
        assert "priority" in result
        assert result["priority"] == 5

    def test_to_dict_includes_priority_with_default(self) -> None:
        """to_dict() should include priority even with default value."""
        todo = Todo(id=1, text="task")  # priority defaults to 0
        result = todo.to_dict()
        assert "priority" in result
        assert result["priority"] == 0

    def test_priority_field_is_int(self) -> None:
        """Priority field should be an integer."""
        todo = Todo(id=1, text="task", priority=10)
        assert isinstance(todo.priority, int)

    def test_priority_can_be_negative(self) -> None:
        """Priority field should accept negative values (for lower priority)."""
        todo = Todo(id=1, text="task", priority=-1)
        assert todo.priority == -1

    def test_priority_can_be_zero_explicitly(self) -> None:
        """Priority can be explicitly set to 0."""
        todo = Todo(id=1, text="task", priority=0)
        assert todo.priority == 0
