"""Tests for Todo priority field (Issue #7207).

This module tests the optional priority field for Todo items.
Priority values: 0=none, 1=low, 2=medium, 3=high
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoPriorityField:
    """Test cases for the optional priority field on Todo."""

    def test_todo_with_priority_can_be_created(self) -> None:
        """Todo should accept an optional priority parameter."""
        todo = Todo(id=1, text="high priority task", priority=3)
        assert todo.priority == 3

    def test_todo_default_priority_is_zero(self) -> None:
        """Todo created without priority should default to 0 (none)."""
        todo = Todo(id=1, text="normal task")
        assert todo.priority == 0

    def test_from_dict_handles_missing_priority(self) -> None:
        """from_dict should set priority=0 when the field is missing (backwards compat)."""
        todo = Todo.from_dict({"id": 1, "text": "legacy task"})
        assert todo.priority == 0

    def test_from_dict_loads_priority_from_data(self) -> None:
        """from_dict should load priority from the data dict when present."""
        todo = Todo.from_dict({"id": 1, "text": "task", "priority": 2})
        assert todo.priority == 2

    def test_to_dict_includes_priority(self) -> None:
        """to_dict should include the priority field in output."""
        todo = Todo(id=1, text="task", priority=1)
        result = todo.to_dict()
        assert "priority" in result
        assert result["priority"] == 1

    def test_to_dict_includes_default_priority(self) -> None:
        """to_dict should include priority even when using default value."""
        todo = Todo(id=1, text="task")
        result = todo.to_dict()
        assert "priority" in result
        assert result["priority"] == 0
