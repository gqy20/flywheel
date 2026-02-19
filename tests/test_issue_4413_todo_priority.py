"""Tests for Todo priority field support (Issue #4413).

These tests verify that:
1. Todo objects support optional priority field (default 2)
2. from_dict validates priority is in 1-3 range
3. CLI add command supports --priority/-p parameter
4. List output shows priority indicator
"""

from __future__ import annotations

import pytest

from flywheel.cli import main
from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


class TestTodoPriorityField:
    """Tests for priority field in Todo dataclass."""

    def test_todo_has_priority_field_with_default(self) -> None:
        """Todo should have priority field with default value 2."""
        todo = Todo(id=1, text="buy milk")
        assert hasattr(todo, "priority")
        assert todo.priority == 2

    def test_todo_priority_can_be_set(self) -> None:
        """Todo priority can be set to 1 (high), 2 (medium), or 3 (low)."""
        # High priority
        todo_high = Todo(id=1, text="urgent task", priority=1)
        assert todo_high.priority == 1

        # Medium priority
        todo_medium = Todo(id=2, text="normal task", priority=2)
        assert todo_medium.priority == 2

        # Low priority
        todo_low = Todo(id=3, text="someday task", priority=3)
        assert todo_low.priority == 3

    def test_from_dict_includes_priority(self) -> None:
        """from_dict should correctly parse priority field."""
        data = {"id": 1, "text": "test task", "priority": 1}
        todo = Todo.from_dict(data)
        assert todo.priority == 1

    def test_from_dict_defaults_priority_to_2(self) -> None:
        """from_dict should default priority to 2 if not provided."""
        data = {"id": 1, "text": "test task"}
        todo = Todo.from_dict(data)
        assert todo.priority == 2

    def test_from_dict_validates_priority_range_low(self) -> None:
        """from_dict should reject priority < 1."""
        data = {"id": 1, "text": "test task", "priority": 0}
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict(data)

    def test_from_dict_validates_priority_range_high(self) -> None:
        """from_dict should reject priority > 3."""
        data = {"id": 1, "text": "test task", "priority": 4}
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict(data)

    def test_from_dict_validates_priority_type(self) -> None:
        """from_dict should reject non-integer priority."""
        data = {"id": 1, "text": "test task", "priority": "high"}
        with pytest.raises(ValueError, match="priority"):
            Todo.from_dict(data)

    def test_to_dict_includes_priority(self) -> None:
        """to_dict should include priority field."""
        todo = Todo(id=1, text="test task", priority=1)
        data = todo.to_dict()
        assert "priority" in data
        assert data["priority"] == 1


class TestTodoPriorityCLI:
    """Tests for CLI --priority parameter."""

    def test_cli_add_supports_priority_short_flag(self, tmp_path, monkeypatch) -> None:
        """CLI add should support -p short flag for priority."""
        db_path = tmp_path / ".todo.json"
        monkeypatch.setattr(
            "sys.argv",
            ["todo", "--db", str(db_path), "add", "-p", "1", "urgent task"],
        )
        result = main()
        assert result == 0

        # Verify priority was saved
        import json

        with open(db_path) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["priority"] == 1

    def test_cli_add_supports_priority_long_flag(self, tmp_path, monkeypatch) -> None:
        """CLI add should support --priority long flag."""
        db_path = tmp_path / ".todo.json"
        monkeypatch.setattr(
            "sys.argv",
            ["todo", "--db", str(db_path), "add", "--priority", "3", "low task"],
        )
        result = main()
        assert result == 0

        # Verify priority was saved
        import json

        with open(db_path) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["priority"] == 3

    def test_cli_add_defaults_priority_to_2(self, tmp_path, monkeypatch) -> None:
        """CLI add should default priority to 2 if not specified."""
        db_path = tmp_path / ".todo.json"
        monkeypatch.setattr(
            "sys.argv",
            ["todo", "--db", str(db_path), "add", "normal task"],
        )
        result = main()
        assert result == 0

        # Verify default priority was saved
        import json

        with open(db_path) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["priority"] == 2

    def test_cli_add_validates_priority_range(self, tmp_path, monkeypatch, capsys) -> None:
        """CLI add should reject invalid priority values."""
        db_path = tmp_path / ".todo.json"
        monkeypatch.setattr(
            "sys.argv",
            ["todo", "--db", str(db_path), "add", "-p", "5", "bad priority task"],
        )
        # argparse validates choices and exits with code 2
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        # Argparse prints error to stderr about invalid choice
        assert "priority" in captured.err.lower() or "invalid" in captured.err.lower()


class TestTodoPriorityFormatter:
    """Tests for priority display in list output."""

    def test_formatter_shows_priority_high(self) -> None:
        """Formatter should show priority indicator for high priority (1)."""
        todo = Todo(id=1, text="urgent task", priority=1)
        output = TodoFormatter.format_todo(todo)
        assert "!" in output  # High priority indicator

    def test_formatter_shows_priority_low(self) -> None:
        """Formatter should show priority indicator for low priority (3)."""
        todo = Todo(id=1, text="someday task", priority=3)
        output = TodoFormatter.format_todo(todo)
        assert "-" in output  # Low priority indicator

    def test_formatter_shows_priority_medium(self) -> None:
        """Formatter should show no indicator or default for medium priority (2)."""
        todo = Todo(id=1, text="normal task", priority=2)
        output = TodoFormatter.format_todo(todo)
        # Medium priority has no special indicator or shows nothing
        assert "!" not in output
        assert "-" not in output
