"""Tests for Todo priority field (Issue #3764).

These tests verify that:
1. Todo instances can set and read priority field (default 0)
2. Todo.from_dict correctly parses priority field (default 0 if missing)
3. Todo.to_dict output includes priority field
4. TodoFormatter.format_todo displays priority markers
"""

from __future__ import annotations

from flywheel.todo import Todo
from flywheel.formatter import TodoFormatter


class TestTodoPriorityField:
    """Tests for the priority field in Todo dataclass."""

    def test_todo_with_priority(self) -> None:
        """Todo instance can set and read priority field."""
        todo = Todo(id=1, text="high priority task", priority=2)
        assert todo.priority == 2

    def test_todo_default_priority_is_zero(self) -> None:
        """Todo default priority should be 0 (no priority)."""
        todo = Todo(id=1, text="normal task")
        assert todo.priority == 0

    def test_todo_priority_range_low(self) -> None:
        """Todo priority can be set to 1 (low)."""
        todo = Todo(id=1, text="low priority", priority=1)
        assert todo.priority == 1

    def test_todo_priority_range_high(self) -> None:
        """Todo priority can be set to 3 (high)."""
        todo = Todo(id=1, text="high priority", priority=3)
        assert todo.priority == 3


class TestTodoFromDictPriority:
    """Tests for Todo.from_dict with priority field."""

    def test_from_dict_with_priority(self) -> None:
        """Todo.from_dict correctly parses priority field."""
        data = {"id": 1, "text": "urgent task", "priority": 3}
        todo = Todo.from_dict(data)
        assert todo.priority == 3

    def test_from_dict_missing_priority_defaults_to_zero(self) -> None:
        """Todo.from_dict defaults priority to 0 if missing."""
        data = {"id": 1, "text": "task without priority"}
        todo = Todo.from_dict(data)
        assert todo.priority == 0

    def test_from_dict_priority_zero(self) -> None:
        """Todo.from_dict handles priority=0 correctly."""
        data = {"id": 1, "text": "task", "priority": 0}
        todo = Todo.from_dict(data)
        assert todo.priority == 0


class TestTodoToDictPriority:
    """Tests for Todo.to_dict with priority field."""

    def test_to_dict_includes_priority(self) -> None:
        """Todo.to_dict output includes priority field."""
        todo = Todo(id=1, text="task", priority=2)
        data = todo.to_dict()
        assert "priority" in data
        assert data["priority"] == 2

    def test_to_dict_includes_default_priority(self) -> None:
        """Todo.to_dict includes priority even when default."""
        todo = Todo(id=1, text="task")
        data = todo.to_dict()
        assert "priority" in data
        assert data["priority"] == 0


class TestTodoFormatterPriority:
    """Tests for TodoFormatter with priority display."""

    def test_format_todo_high_priority(self) -> None:
        """TodoFormatter.format_todo displays !!! for high priority (3)."""
        todo = Todo(id=1, text="urgent", priority=3)
        result = TodoFormatter.format_todo(todo)
        assert "!!!" in result

    def test_format_todo_medium_priority(self) -> None:
        """TodoFormatter.format_todo displays !! for medium priority (2)."""
        todo = Todo(id=1, text="important", priority=2)
        result = TodoFormatter.format_todo(todo)
        assert "!!" in result

    def test_format_todo_low_priority(self) -> None:
        """TodoFormatter.format_todo displays ! for low priority (1)."""
        todo = Todo(id=1, text="minor", priority=1)
        result = TodoFormatter.format_todo(todo)
        assert "!" in result

    def test_format_todo_no_priority(self) -> None:
        """TodoFormatter.format_todo shows no marker for no priority (0)."""
        todo = Todo(id=1, text="normal", priority=0)
        result = TodoFormatter.format_todo(todo)
        assert "!" not in result

    def test_format_todo_still_shows_status_and_id(self) -> None:
        """TodoFormatter.format_todo still shows status and id with priority."""
        todo = Todo(id=1, text="task", done=False, priority=2)
        result = TodoFormatter.format_todo(todo)
        assert "[ ]" in result  # status
        assert "1" in result  # id
        assert "!!" in result  # priority
        assert "task" in result  # text
