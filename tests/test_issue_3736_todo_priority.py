"""Tests for Todo priority field (Issue #3736).

These tests verify that:
1. Todo objects have a priority field with default value 2 (low)
2. from_dict validates priority is in range 0-2
3. CLI add command supports --priority/-p argument
"""

from __future__ import annotations

import pytest

from flywheel.cli import build_parser
from flywheel.todo import Todo


class TestTodoPriorityField:
    """Tests for Todo priority field."""

    def test_todo_has_priority_field_with_default(self) -> None:
        """Todo should have priority field with default value 2 (low)."""
        todo = Todo(id=1, text="test task")
        assert hasattr(todo, "priority")
        assert todo.priority == 2

    def test_todo_priority_can_be_set(self) -> None:
        """Todo priority can be explicitly set."""
        todo_high = Todo(id=1, text="urgent", priority=0)
        assert todo_high.priority == 0

        todo_medium = Todo(id=2, text="normal", priority=1)
        assert todo_medium.priority == 1

        todo_low = Todo(id=3, text="later", priority=2)
        assert todo_low.priority == 2

    def test_todo_to_dict_includes_priority(self) -> None:
        """Todo.to_dict should include priority field."""
        todo = Todo(id=1, text="test", priority=1)
        data = todo.to_dict()
        assert "priority" in data
        assert data["priority"] == 1

    def test_from_dict_with_valid_priority(self) -> None:
        """Todo.from_dict should accept valid priority values (0-2)."""
        for priority in [0, 1, 2]:
            todo = Todo.from_dict({"id": 1, "text": "test", "priority": priority})
            assert todo.priority == priority

    def test_from_dict_without_priority_uses_default(self) -> None:
        """Todo.from_dict should default to priority=2 when not specified."""
        todo = Todo.from_dict({"id": 1, "text": "test"})
        assert todo.priority == 2

    def test_from_dict_rejects_priority_above_2(self) -> None:
        """Todo.from_dict should reject priority values > 2."""
        with pytest.raises(ValueError, match=r"priority|invalid|range"):
            Todo.from_dict({"id": 1, "text": "test", "priority": 3})

    def test_from_dict_rejects_negative_priority(self) -> None:
        """Todo.from_dict should reject negative priority values."""
        with pytest.raises(ValueError, match=r"priority|invalid|range"):
            Todo.from_dict({"id": 1, "text": "test", "priority": -1})


class TestTodoPriorityCli:
    """Tests for CLI --priority argument."""

    def test_add_parser_has_priority_argument(self) -> None:
        """add subcommand should have --priority/-p argument."""
        parser = build_parser()
        # Test that --priority is accepted
        args = parser.parse_args(["add", "test task", "--priority", "1"])
        assert hasattr(args, "priority")
        assert args.priority == 1

    def test_add_parser_priority_short_flag(self) -> None:
        """add subcommand should accept -p as short form of --priority."""
        parser = build_parser()
        args = parser.parse_args(["add", "test task", "-p", "0"])
        assert args.priority == 0

    def test_add_parser_priority_default(self) -> None:
        """add subcommand priority should default to 2 when not specified."""
        parser = build_parser()
        args = parser.parse_args(["add", "test task"])
        assert args.priority == 2
