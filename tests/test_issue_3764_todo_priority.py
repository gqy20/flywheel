"""Tests for Todo priority field (Issue #3764).

These tests verify that:
1. Todo instances have a priority field with default value 0
2. Todo.from_dict correctly parses priority field (defaults to 0 when missing)
3. Todo.to_dict includes priority field
4. TodoFormatter.format_todo displays priority markers (!, !!, !!!)
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


class TestTodoPriorityField:
    """Test the priority field on Todo dataclass."""

    def test_todo_has_priority_field_with_default_zero(self) -> None:
        """Todo instance should have priority field defaulting to 0."""
        todo = Todo(id=1, text="test task")
        assert todo.priority == 0

    def test_todo_priority_can_be_set(self) -> None:
        """Todo priority can be explicitly set."""
        todo = Todo(id=1, text="test task", priority=2)
        assert todo.priority == 2

    def test_todo_priority_high_value(self) -> None:
        """Todo priority can be set to maximum value (3)."""
        todo = Todo(id=1, text="urgent task", priority=3)
        assert todo.priority == 3


class TestTodoFromDictPriority:
    """Test Todo.from_dict handling of priority field."""

    def test_from_dict_parses_priority(self) -> None:
        """from_dict should parse priority from dict."""
        todo = Todo.from_dict({"id": 1, "text": "test", "priority": 3})
        assert todo.priority == 3

    def test_from_dict_defaults_priority_to_zero_when_missing(self) -> None:
        """from_dict should default priority to 0 when not in dict."""
        todo = Todo.from_dict({"id": 1, "text": "test"})
        assert todo.priority == 0

    def test_from_dict_defaults_priority_to_zero_when_none(self) -> None:
        """from_dict should default priority to 0 when value is None."""
        todo = Todo.from_dict({"id": 1, "text": "test", "priority": None})
        assert todo.priority == 0


class TestTodoToDictPriority:
    """Test Todo.to_dict includes priority field."""

    def test_to_dict_includes_priority(self) -> None:
        """to_dict should include priority field."""
        todo = Todo(id=1, text="test", priority=2)
        result = todo.to_dict()
        assert "priority" in result
        assert result["priority"] == 2

    def test_to_dict_includes_default_priority(self) -> None:
        """to_dict should include priority field even with default value."""
        todo = Todo(id=1, text="test")
        result = todo.to_dict()
        assert "priority" in result
        assert result["priority"] == 0


class TestTodoFormatterPriorityDisplay:
    """Test TodoFormatter.format_todo displays priority markers."""

    def test_format_todo_shows_no_marker_for_priority_zero(self) -> None:
        """format_todo should show no marker for priority 0."""
        todo = Todo(id=1, text="normal task", priority=0)
        result = TodoFormatter.format_todo(todo)
        assert "!" not in result or result.count("!") == 0

    def test_format_todo_shows_single_exclamation_for_priority_1(self) -> None:
        """format_todo should show '!' for priority 1 (low)."""
        todo = Todo(id=1, text="low priority", priority=1)
        result = TodoFormatter.format_todo(todo)
        assert "!" in result

    def test_format_todo_shows_double_exclamation_for_priority_2(self) -> None:
        """format_todo should show '!!' for priority 2 (medium)."""
        todo = Todo(id=1, text="medium priority", priority=2)
        result = TodoFormatter.format_todo(todo)
        assert "!!" in result

    def test_format_todo_shows_triple_exclamation_for_priority_3(self) -> None:
        """format_todo should show '!!!' for priority 3 (high)."""
        todo = Todo(id=1, text="high priority", priority=3)
        result = TodoFormatter.format_todo(todo)
        assert "!!!" in result
