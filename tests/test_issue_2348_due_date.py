"""Tests for due_date field (Issue #2348).

These tests verify that:
1. Todo objects have an optional due_date field
2. due_date defaults to None
3. due_date accepts ISO format date strings (YYYY-MM-DD)
4. from_dict validates due_date format
5. formatter marks overdue tasks
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_todo_due_date_defaults_to_none() -> None:
    """Todo should have due_date field that defaults to None."""
    todo = Todo(id=1, text="buy milk")
    assert hasattr(todo, "due_date")
    assert todo.due_date is None


def test_todo_accepts_valid_iso_date() -> None:
    """Todo should accept valid ISO date string (YYYY-MM-DD)."""
    todo = Todo(id=1, text="buy milk", due_date="2025-12-31")
    assert todo.due_date == "2025-12-31"


def test_todo_from_dict_accepts_valid_due_date() -> None:
    """Todo.from_dict should accept valid due_date in ISO format."""
    data = {
        "id": 1,
        "text": "buy milk",
        "done": False,
        "due_date": "2025-12-31",
    }
    todo = Todo.from_dict(data)
    assert todo.due_date == "2025-12-31"


def test_todo_from_dict_rejects_invalid_date_format() -> None:
    """Todo.from_dict should reject invalid date formats."""
    # Not a date at all
    data1 = {"id": 1, "text": "buy milk", "done": False, "due_date": "not-a-date"}
    with pytest.raises(ValueError, match="due_date"):
        Todo.from_dict(data1)

    # Wrong format
    data2 = {"id": 1, "text": "buy milk", "done": False, "due_date": "12/31/2025"}
    with pytest.raises(ValueError, match="due_date"):
        Todo.from_dict(data2)

    # Invalid date (Feb 30 doesn't exist)
    data3 = {"id": 1, "text": "buy milk", "done": False, "due_date": "2025-02-30"}
    with pytest.raises(ValueError, match="due_date"):
        Todo.from_dict(data3)


def test_todo_from_dict_handles_missing_due_date() -> None:
    """Todo.from_dict should handle missing due_date (defaults to None)."""
    data = {
        "id": 1,
        "text": "buy milk",
        "done": False,
    }
    todo = Todo.from_dict(data)
    assert todo.due_date is None


def test_todo_from_dict_handles_none_due_date() -> None:
    """Todo.from_dict should handle explicit None for due_date."""
    data = {
        "id": 1,
        "text": "buy milk",
        "done": False,
        "due_date": None,
    }
    todo = Todo.from_dict(data)
    assert todo.due_date is None


def test_todo_to_dict_includes_due_date() -> None:
    """Todo.to_dict should include due_date field."""
    todo = Todo(id=1, text="buy milk", due_date="2025-12-31")
    data = todo.to_dict()
    assert data["due_date"] == "2025-12-31"


def test_todo_formatter_marks_overdue_tasks() -> None:
    """TodoFormatter should mark overdue tasks with OVERDUE prefix."""
    # Create a todo with a past due_date (yesterday)
    past_date = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    past_date = past_date - timedelta(days=1)
    past_date_str = past_date.strftime("%Y-%m-%d")

    overdue_todo = Todo(id=1, text="overdue task", done=False, due_date=past_date_str)
    result = TodoFormatter.format_todo(overdue_todo)

    assert "OVERDUE" in result


def test_todo_formatter_does_not_mark_future_tasks() -> None:
    """TodoFormatter should not mark tasks with future due dates."""
    future_todo = Todo(id=1, text="future task", done=False, due_date="2099-12-31")
    result = TodoFormatter.format_todo(future_todo)

    assert "OVERDUE" not in result


def test_todo_formatter_does_not_mark_tasks_without_due_date() -> None:
    """TodoFormatter should not mark tasks without due_date."""
    todo = Todo(id=1, text="no deadline task", done=False)
    result = TodoFormatter.format_todo(todo)

    assert "OVERDUE" not in result
