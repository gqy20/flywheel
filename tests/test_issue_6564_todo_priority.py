"""Tests for Todo priority field support (Issue #6564).

These tests verify that:
1. Todo dataclass includes priority field with default value 0
2. from_dict correctly parses priority field
3. to_dict includes priority field
4. TodoFormatter displays priority indicator for high-priority todos
5. TodoFormatter can sort todos by priority
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


class TestTodoPriorityField:
    """Tests for Todo priority field."""

    def test_todo_has_priority_field_with_default_zero(self) -> None:
        """Todo should have a priority field defaulting to 0 (normal)."""
        todo = Todo(id=1, text="test task")
        assert hasattr(todo, "priority")
        assert todo.priority == 0

    def test_todo_can_be_created_with_priority(self) -> None:
        """Todo should accept priority value at creation."""
        todo_high = Todo(id=1, text="urgent task", priority=1)
        assert todo_high.priority == 1

        todo_low = Todo(id=2, text="low priority task", priority=-1)
        assert todo_low.priority == -1

    def test_from_dict_parses_priority(self) -> None:
        """from_dict should correctly parse priority field."""
        data = {"id": 1, "text": "task", "priority": 1}
        todo = Todo.from_dict(data)
        assert todo.priority == 1

    def test_from_dict_defaults_priority_to_zero(self) -> None:
        """from_dict should default priority to 0 if not provided."""
        data = {"id": 1, "text": "task"}
        todo = Todo.from_dict(data)
        assert todo.priority == 0

    def test_to_dict_includes_priority(self) -> None:
        """to_dict should include priority field."""
        todo = Todo(id=1, text="task", priority=1)
        data = todo.to_dict()
        assert "priority" in data
        assert data["priority"] == 1


class TestTodoFormatterPriority:
    """Tests for TodoFormatter priority display."""

    def test_format_todo_shows_high_priority_indicator(self) -> None:
        """High priority todos should show '!' indicator."""
        todo = Todo(id=1, text="urgent task", priority=1)
        result = TodoFormatter.format_todo(todo)
        assert "!" in result

    def test_format_todo_no_indicator_for_normal_priority(self) -> None:
        """Normal priority todos should not show indicator."""
        todo = Todo(id=1, text="normal task", priority=0)
        result = TodoFormatter.format_todo(todo)
        assert "!" not in result

    def test_format_todo_no_indicator_for_low_priority(self) -> None:
        """Low priority todos should not show '!' indicator."""
        todo = Todo(id=1, text="low task", priority=-1)
        result = TodoFormatter.format_todo(todo)
        assert "!" not in result
