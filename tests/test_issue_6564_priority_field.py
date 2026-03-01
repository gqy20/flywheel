"""Regression tests for Issue #6564: Todo priority field and sorting support.

This test file ensures that:
1. Todo dataclass includes a priority field with default value 0
2. from_dict correctly parses priority field
3. to_dict includes priority field
4. High priority todos are marked with '!' in formatted output
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


class TestTodoPriorityField:
    """Tests for Todo.priority field."""

    def test_todo_has_priority_field_with_default_zero(self) -> None:
        """Todo should have a priority field that defaults to 0 (normal)."""
        todo = Todo(id=1, text="buy milk")
        assert hasattr(todo, "priority")
        assert todo.priority == 0

    def test_todo_can_be_created_with_priority(self) -> None:
        """Todo should accept priority value at creation."""
        todo_high = Todo(id=1, text="urgent task", priority=1)
        assert todo_high.priority == 1

        todo_low = Todo(id=2, text="low priority task", priority=-1)
        assert todo_low.priority == -1

    def test_from_dict_parses_priority_field(self) -> None:
        """from_dict should correctly parse the priority field."""
        data = {"id": 1, "text": "task", "priority": 1}
        todo = Todo.from_dict(data)
        assert todo.priority == 1

    def test_from_dict_defaults_priority_to_zero(self) -> None:
        """from_dict should default priority to 0 if not provided."""
        data = {"id": 1, "text": "task"}
        todo = Todo.from_dict(data)
        assert todo.priority == 0

    def test_to_dict_includes_priority(self) -> None:
        """to_dict should include the priority field."""
        todo = Todo(id=1, text="task", priority=1)
        data = todo.to_dict()
        assert "priority" in data
        assert data["priority"] == 1


class TestTodoFormatterPriority:
    """Tests for priority marker in TodoFormatter."""

    def test_format_todo_marks_high_priority(self) -> None:
        """High priority (1) todos should be marked with '!'."""
        todo = Todo(id=1, text="urgent task", priority=1)
        result = TodoFormatter.format_todo(todo)
        assert "!" in result

    def test_format_todo_no_marker_for_normal_priority(self) -> None:
        """Normal priority (0) todos should not have '!' marker."""
        todo = Todo(id=1, text="normal task", priority=0)
        result = TodoFormatter.format_todo(todo)
        # The "!" should not appear as a priority marker (but could be in text)
        # Check that the format doesn't include priority marker prefix
        assert not result.startswith("!")

    def test_format_todo_no_marker_for_low_priority(self) -> None:
        """Low priority (-1) todos should not have '!' marker."""
        todo = Todo(id=1, text="low priority task", priority=-1)
        result = TodoFormatter.format_todo(todo)
        # Low priority should not have the high priority marker
        # Check the result doesn't have "!" as priority indicator
        assert not result.startswith("!")
