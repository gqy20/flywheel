"""Tests for Todo priority field support (Issue #4413).

These tests verify that:
1. Todo supports optional priority field with default value 2
2. from_dict validates priority is in 1-3 range
3. CLI add command supports --priority/-p parameter
4. list output shows priority indicator
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


# Tests for Todo dataclass priority field
def test_todo_has_priority_field_with_default() -> None:
    """Todo should have a priority field with default value 2 (medium)."""
    todo = Todo(id=1, text="task")
    assert hasattr(todo, "priority")
    assert todo.priority == 2


def test_todo_priority_can_be_set() -> None:
    """Todo priority should be settable to 1 (high), 2 (medium), or 3 (low)."""
    todo_high = Todo(id=1, text="urgent task", priority=1)
    assert todo_high.priority == 1

    todo_medium = Todo(id=2, text="normal task", priority=2)
    assert todo_medium.priority == 2

    todo_low = Todo(id=3, text="later task", priority=3)
    assert todo_low.priority == 3


# Tests for from_dict validation
def test_from_dict_accepts_valid_priority() -> None:
    """Todo.from_dict should accept valid priority values 1-3."""
    for prio in [1, 2, 3]:
        todo = Todo.from_dict({"id": 1, "text": "task", "priority": prio})
        assert todo.priority == prio


def test_from_dict_uses_default_priority_when_missing() -> None:
    """Todo.from_dict should use default priority 2 when not specified."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.priority == 2


def test_from_dict_rejects_priority_below_range() -> None:
    """Todo.from_dict should reject priority value 0 (below valid range)."""
    with pytest.raises(ValueError, match=r"invalid.*priority|priority.*range|priority.*1.*3"):
        Todo.from_dict({"id": 1, "text": "task", "priority": 0})


def test_from_dict_rejects_priority_above_range() -> None:
    """Todo.from_dict should reject priority value 4 (above valid range)."""
    with pytest.raises(ValueError, match=r"invalid.*priority|priority.*range|priority.*1.*3"):
        Todo.from_dict({"id": 1, "text": "task", "priority": 4})


def test_from_dict_rejects_negative_priority() -> None:
    """Todo.from_dict should reject negative priority values."""
    with pytest.raises(ValueError, match=r"invalid.*priority|priority.*range|priority.*1.*3"):
        Todo.from_dict({"id": 1, "text": "task", "priority": -1})


def test_from_dict_rejects_non_integer_priority() -> None:
    """Todo.from_dict should reject non-integer priority values."""
    with pytest.raises(ValueError, match=r"invalid.*priority|priority.*integer"):
        Todo.from_dict({"id": 1, "text": "task", "priority": "high"})


# Tests for to_dict round-trip
def test_to_dict_includes_priority() -> None:
    """Todo.to_dict should include priority field."""
    todo = Todo(id=1, text="task", priority=1)
    data = todo.to_dict()
    assert "priority" in data
    assert data["priority"] == 1


def test_priority_round_trip() -> None:
    """Priority should be preserved through to_dict/from_dict round-trip."""
    original = Todo(id=1, text="task", priority=3)
    restored = Todo.from_dict(original.to_dict())
    assert restored.priority == original.priority


# Tests for CLI --priority parameter
def test_cli_add_with_priority_short_flag(tmp_path) -> None:
    """CLI add command should accept -p short flag for priority."""
    from flywheel.cli import main

    db_path = tmp_path / "test.json"
    result = main(["--db", str(db_path), "add", "urgent task", "-p", "1"])

    assert result == 0

    # Verify the todo was saved with priority 1
    import json
    with open(db_path) as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["priority"] == 1


def test_cli_add_with_priority_long_flag(tmp_path) -> None:
    """CLI add command should accept --priority long flag."""
    from flywheel.cli import main

    db_path = tmp_path / "test.json"
    result = main(["--db", str(db_path), "add", "low priority task", "--priority", "3"])

    assert result == 0

    # Verify the todo was saved with priority 3
    import json
    with open(db_path) as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["priority"] == 3


def test_cli_add_default_priority(tmp_path) -> None:
    """CLI add command should default to priority 2 when not specified."""
    from flywheel.cli import main

    db_path = tmp_path / "test.json"
    result = main(["--db", str(db_path), "add", "normal task"])

    assert result == 0

    # Verify the todo was saved with default priority 2
    import json
    with open(db_path) as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["priority"] == 2


# Tests for formatter priority indicator
def test_formatter_shows_priority_marker() -> None:
    """TodoFormatter should show priority markers in output."""
    from flywheel.formatter import TodoFormatter

    todo_high = Todo(id=1, text="urgent", priority=1)
    todo_medium = Todo(id=2, text="normal", priority=2)
    todo_low = Todo(id=3, text="later", priority=3)

    high_output = TodoFormatter.format_todo(todo_high)
    medium_output = TodoFormatter.format_todo(todo_medium)
    low_output = TodoFormatter.format_todo(todo_low)

    # High priority should show "!"
    assert "!" in high_output

    # Medium priority should show "-"
    assert "-" in medium_output

    # Low priority should show "."
    assert "." in low_output


def test_formatter_list_includes_priority() -> None:
    """TodoFormatter.format_list should include priority markers."""
    from flywheel.formatter import TodoFormatter

    todos = [
        Todo(id=1, text="urgent", priority=1),
        Todo(id=2, text="normal", priority=2),
        Todo(id=3, text="later", priority=3),
    ]

    output = TodoFormatter.format_list(todos)

    # All priority markers should appear in output
    assert "!" in output  # high
    assert "-" in output  # medium
    assert "." in output  # low
