"""Tests for Todo priority field (Issue #3736).

These tests verify that:
1. Todo objects have a priority field with default value 2 (low)
2. Priority can be set to 0 (high), 1 (medium), or 2 (low)
3. from_dict validates priority is in range 0-2
4. CLI add command supports --priority/-p parameter
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoPriorityField:
    """Tests for Todo priority field."""

    def test_todo_has_priority_field_with_default_2(self) -> None:
        """Todo should have priority field defaulting to 2 (low)."""
        todo = Todo(id=1, text="test task")
        assert hasattr(todo, "priority")
        assert todo.priority == 2

    def test_todo_can_be_created_with_priority_0(self) -> None:
        """Todo should accept priority=0 (high)."""
        todo = Todo(id=1, text="urgent task", priority=0)
        assert todo.priority == 0

    def test_todo_can_be_created_with_priority_1(self) -> None:
        """Todo should accept priority=1 (medium)."""
        todo = Todo(id=1, text="medium task", priority=1)
        assert todo.priority == 1

    def test_todo_can_be_created_with_priority_2(self) -> None:
        """Todo should accept priority=2 (low)."""
        todo = Todo(id=1, text="low task", priority=2)
        assert todo.priority == 2

    def test_from_dict_accepts_valid_priority(self) -> None:
        """from_dict should accept priority in range 0-2."""
        for priority in [0, 1, 2]:
            todo = Todo.from_dict({"id": 1, "text": "test", "priority": priority})
            assert todo.priority == priority

    def test_from_dict_rejects_priority_3(self) -> None:
        """from_dict should reject priority=3 (out of range)."""
        try:
            Todo.from_dict({"id": 1, "text": "test", "priority": 3})
            raise AssertionError("Expected ValueError for priority=3")
        except ValueError as e:
            assert "priority" in str(e).lower()

    def test_from_dict_rejects_negative_priority(self) -> None:
        """from_dict should reject negative priority."""
        try:
            Todo.from_dict({"id": 1, "text": "test", "priority": -1})
            raise AssertionError("Expected ValueError for priority=-1")
        except ValueError as e:
            assert "priority" in str(e).lower()

    def test_from_dict_defaults_priority_to_2(self) -> None:
        """from_dict should default priority to 2 if not specified."""
        todo = Todo.from_dict({"id": 1, "text": "test"})
        assert todo.priority == 2

    def test_to_dict_includes_priority(self) -> None:
        """to_dict should include priority field."""
        todo = Todo(id=1, text="test", priority=0)
        data = todo.to_dict()
        assert "priority" in data
        assert data["priority"] == 0


class TestTodoPriorityCLI:
    """Tests for CLI priority support."""

    def test_cli_add_accepts_priority_argument(self) -> None:
        """CLI add command should accept --priority argument."""
        from flywheel.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["add", "test task", "--priority", "0"])
        assert hasattr(args, "priority")
        assert args.priority == 0

    def test_cli_add_accepts_short_priority_argument(self) -> None:
        """CLI add command should accept -p as short form."""
        from flywheel.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["add", "test task", "-p", "1"])
        assert args.priority == 1

    def test_cli_add_priority_defaults_to_2(self) -> None:
        """CLI add command should default priority to 2."""
        from flywheel.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["add", "test task"])
        assert args.priority == 2
