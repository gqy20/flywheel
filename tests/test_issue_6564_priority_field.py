"""Tests for Todo priority field (Issue #6564).

These tests verify that:
1. Todo dataclass includes priority field with default value 0
2. from_dict correctly parses priority field
3. to_dict includes priority field
4. High priority todos are marked with '!' in format_todo
5. TodoFormatter.format_list sorts by priority (high first)
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


class TestTodoPriorityField:
    """Tests for Todo priority field."""

    def test_todo_has_priority_field_with_default_zero(self) -> None:
        """Todo should have a priority field with default value 0."""
        todo = Todo(id=1, text="test task")
        assert hasattr(todo, "priority")
        assert todo.priority == 0

    def test_todo_priority_can_be_set(self) -> None:
        """Todo priority can be set to high (1) or low (-1)."""
        high_priority = Todo(id=1, text="urgent", priority=1)
        assert high_priority.priority == 1

        low_priority = Todo(id=2, text="later", priority=-1)
        assert low_priority.priority == -1

    def test_from_dict_parses_priority(self) -> None:
        """from_dict should correctly parse priority field."""
        data = {"id": 1, "text": "test", "priority": 1}
        todo = Todo.from_dict(data)
        assert todo.priority == 1

    def test_from_dict_defaults_priority_to_zero(self) -> None:
        """from_dict should default priority to 0 if not provided."""
        data = {"id": 1, "text": "test"}
        todo = Todo.from_dict(data)
        assert todo.priority == 0

    def test_to_dict_includes_priority(self) -> None:
        """to_dict should include priority field."""
        todo = Todo(id=1, text="test", priority=1)
        data = todo.to_dict()
        assert "priority" in data
        assert data["priority"] == 1


class TestTodoFormatterPriority:
    """Tests for TodoFormatter priority display."""

    def test_format_todo_shows_high_priority_marker(self) -> None:
        """High priority todos should be marked with '!' in format_todo."""
        todo = Todo(id=1, text="urgent task", priority=1)
        result = TodoFormatter.format_todo(todo)
        assert "!" in result

    def test_format_todo_no_marker_for_normal_priority(self) -> None:
        """Normal priority todos should not have '!' marker."""
        todo = Todo(id=1, text="normal task", priority=0)
        result = TodoFormatter.format_todo(todo)
        # Should not have high priority marker for normal tasks
        # The '!' should only appear for high priority (priority=1)
        assert "!" not in result or result.count("!") == 0

    def test_format_list_sorts_by_priority(self) -> None:
        """format_list should sort todos by priority (high first)."""
        low = Todo(id=1, text="low priority", priority=-1)
        normal = Todo(id=2, text="normal priority", priority=0)
        high = Todo(id=3, text="high priority", priority=1)

        # Pass in mixed order
        result = TodoFormatter.format_list([normal, low, high])

        # High priority should appear before low priority in output
        lines = result.split("\n")
        high_line = next(i for i, line in enumerate(lines) if "high priority" in line)
        low_line = next(i for i, line in enumerate(lines) if "low priority" in line)

        assert high_line < low_line, "High priority should appear before low priority"
