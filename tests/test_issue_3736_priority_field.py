"""Tests for Todo priority field (Issue #3736).

These tests verify that:
1. Todo dataclass has a priority field with default value 2 (low)
2. Priority values 0 (high), 1 (medium), 2 (low) are accepted
3. from_dict rejects invalid priority values (negative, > 2)
4. CLI add command supports --priority/-p argument
"""

from __future__ import annotations

import pytest

from flywheel.cli import build_parser
from flywheel.todo import Todo


class TestTodoPriorityField:
    """Tests for the Todo priority field."""

    def test_todo_default_priority_is_two(self) -> None:
        """Todo should have default priority=2 (low)."""
        todo = Todo(id=1, text="test task")
        assert todo.priority == 2

    def test_todo_with_priority_zero(self) -> None:
        """Todo should accept priority=0 (high)."""
        todo = Todo(id=1, text="urgent task", priority=0)
        assert todo.priority == 0

    def test_todo_with_priority_one(self) -> None:
        """Todo should accept priority=1 (medium)."""
        todo = Todo(id=1, text="medium task", priority=1)
        assert todo.priority == 1

    def test_todo_with_priority_two(self) -> None:
        """Todo should accept priority=2 (low)."""
        todo = Todo(id=1, text="low task", priority=2)
        assert todo.priority == 2


class TestTodoFromDictPriorityValidation:
    """Tests for priority validation in from_dict."""

    def test_from_dict_with_valid_priority_zero(self) -> None:
        """from_dict should accept priority=0."""
        todo = Todo.from_dict({"id": 1, "text": "task", "priority": 0})
        assert todo.priority == 0

    def test_from_dict_with_valid_priority_one(self) -> None:
        """from_dict should accept priority=1."""
        todo = Todo.from_dict({"id": 1, "text": "task", "priority": 1})
        assert todo.priority == 1

    def test_from_dict_with_valid_priority_two(self) -> None:
        """from_dict should accept priority=2."""
        todo = Todo.from_dict({"id": 1, "text": "task", "priority": 2})
        assert todo.priority == 2

    def test_from_dict_with_default_priority(self) -> None:
        """from_dict should use default priority=2 when not specified."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        assert todo.priority == 2

    def test_from_dict_rejects_priority_three(self) -> None:
        """from_dict should reject priority=3 (out of range)."""
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict({"id": 1, "text": "task", "priority": 3})

    def test_from_dict_rejects_negative_priority(self) -> None:
        """from_dict should reject priority=-1 (out of range)."""
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict({"id": 1, "text": "task", "priority": -1})

    def test_from_dict_rejects_non_integer_priority(self) -> None:
        """from_dict should reject non-integer priority."""
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict({"id": 1, "text": "task", "priority": "high"})


class TestTodoToDictIncludesPriority:
    """Tests that to_dict includes priority."""

    def test_to_dict_includes_priority(self) -> None:
        """to_dict should include the priority field."""
        todo = Todo(id=1, text="task", priority=0)
        data = todo.to_dict()
        assert "priority" in data
        assert data["priority"] == 0


class TestCliPriorityArgument:
    """Tests for CLI --priority argument support."""

    def test_add_parser_has_priority_argument(self) -> None:
        """add subparser should have --priority argument."""
        parser = build_parser()
        # Parse with add command
        args = parser.parse_args(["add", "test task", "--priority", "0"])
        assert hasattr(args, "priority")
        assert args.priority == 0

    def test_add_parser_has_short_priority_argument(self) -> None:
        """add subparser should have -p short argument."""
        parser = build_parser()
        args = parser.parse_args(["add", "test task", "-p", "1"])
        assert args.priority == 1

    def test_add_default_priority(self) -> None:
        """add command should default to priority 2 if not specified."""
        parser = build_parser()
        args = parser.parse_args(["add", "test task"])
        assert args.priority == 2
