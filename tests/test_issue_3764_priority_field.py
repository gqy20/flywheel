"""Tests for Issue #3764: Todo priority field.

These tests verify that:
1. Todo instances can set and read priority field (default 0)
2. Todo.from_dict correctly parses priority field (missing defaults to 0)
3. Todo.to_dict output includes priority field
4. TodoFormatter.format_todo displays priority markers (!, !!, !!!)
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


class TestTodoPriorityField:
    """Tests for Todo priority field."""

    def test_todo_has_priority_field_with_default_zero(self) -> None:
        """Todo should have a priority field with default value 0."""
        todo = Todo(id=1, text="buy milk")
        assert todo.priority == 0

    def test_todo_priority_can_be_set(self) -> None:
        """Todo priority can be set to a specific value."""
        todo = Todo(id=1, text="important task", priority=2)
        assert todo.priority == 2

    def test_todo_priority_high_value(self) -> None:
        """Todo priority can be set to high (3)."""
        todo = Todo(id=1, text="urgent task", priority=3)
        assert todo.priority == 3


class TestTodoFromDictPriority:
    """Tests for Todo.from_dict with priority field."""

    def test_from_dict_parses_priority_field(self) -> None:
        """from_dict should correctly parse priority field."""
        todo = Todo.from_dict({"id": 1, "text": "x", "priority": 3})
        assert todo.priority == 3

    def test_from_dict_priority_defaults_to_zero(self) -> None:
        """from_dict should default priority to 0 when missing."""
        todo = Todo.from_dict({"id": 1, "text": "x"})
        assert todo.priority == 0

    def test_from_dict_priority_with_other_fields(self) -> None:
        """from_dict should handle priority alongside other optional fields."""
        todo = Todo.from_dict(
            {
                "id": 1,
                "text": "complete task",
                "done": True,
                "priority": 2,
                "created_at": "2024-01-01T00:00:00+00:00",
                "updated_at": "2024-01-02T00:00:00+00:00",
            }
        )
        assert todo.priority == 2
        assert todo.done is True


class TestTodoToDictPriority:
    """Tests for Todo.to_dict with priority field."""

    def test_to_dict_includes_priority(self) -> None:
        """to_dict should include priority field."""
        todo = Todo(id=1, text="task", priority=2)
        result = todo.to_dict()
        assert "priority" in result
        assert result["priority"] == 2

    def test_to_dict_includes_default_priority(self) -> None:
        """to_dict should include priority field even with default value."""
        todo = Todo(id=1, text="task")
        result = todo.to_dict()
        assert "priority" in result
        assert result["priority"] == 0


class TestTodoFormatterPriority:
    """Tests for TodoFormatter.format_todo with priority markers."""

    def test_format_todo_shows_high_priority_marker(self) -> None:
        """High priority (3) should show !!! marker."""
        todo = Todo(id=1, text="urgent task", priority=3)
        result = TodoFormatter.format_todo(todo)
        assert "!!!" in result

    def test_format_todo_shows_medium_priority_marker(self) -> None:
        """Medium priority (2) should show !! marker."""
        todo = Todo(id=1, text="important task", priority=2)
        result = TodoFormatter.format_todo(todo)
        assert "!!" in result

    def test_format_todo_shows_low_priority_marker(self) -> None:
        """Low priority (1) should show ! marker."""
        todo = Todo(id=1, text="minor task", priority=1)
        result = TodoFormatter.format_todo(todo)
        # Should have single ! but not multiple
        assert "!" in result
        assert "!!!" not in result
        assert "!!" not in result or result.count("!") == 1

    def test_format_todo_no_priority_marker_for_zero(self) -> None:
        """No priority (0) should show no marker."""
        todo = Todo(id=1, text="normal task", priority=0)
        result = TodoFormatter.format_todo(todo)
        assert "!" not in result

    def test_format_todo_priority_format_structure(self) -> None:
        """Priority marker should appear in expected position in output."""
        todo = Todo(id=1, text="task", priority=3)
        result = TodoFormatter.format_todo(todo)
        # Should contain status, id, priority marker, and text
        assert "[ ]" in result  # status
        assert "1" in result  # id
        assert "!!!" in result  # priority marker
        assert "task" in result  # text
