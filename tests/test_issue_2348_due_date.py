"""Regression tests for Issue #2348: Add due_date field to Todo items.

This test file ensures that:
1. Todo class supports optional due_date field
2. due_date accepts ISO format date strings (YYYY-MM-DD)
3. from_dict validates date format and rejects invalid formats
4. from_dict handles missing due_date for backward compatibility
5. to_dict includes due_date in output
6. TodoFormatter marks overdue tasks
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_todo_creation_without_due_date() -> None:
    """Todo creation without due_date should default to None."""
    todo = Todo(id=1, text="Buy milk")
    assert todo.due_date is None


def test_todo_creation_with_valid_due_date() -> None:
    """Todo creation with valid ISO date should store the date."""
    todo = Todo(id=1, text="Buy milk", due_date="2025-12-31")
    assert todo.due_date == "2025-12-31"


def test_todo_to_dict_includes_due_date() -> None:
    """Todo.to_dict should include due_date field."""
    todo = Todo(id=1, text="Buy milk", due_date="2025-12-31")
    data = todo.to_dict()
    assert "due_date" in data
    assert data["due_date"] == "2025-12-31"


def test_todo_to_dict_with_none_due_date() -> None:
    """Todo.to_dict should include due_date even when None."""
    todo = Todo(id=1, text="Buy milk")
    data = todo.to_dict()
    assert "due_date" in data
    assert data["due_date"] is None


def test_todo_from_dict_without_due_date() -> None:
    """Todo.from_dict should handle missing due_date key (backward compatibility)."""
    data = {"id": 1, "text": "Buy milk", "done": False}
    todo = Todo.from_dict(data)
    assert todo.due_date is None


def test_todo_from_dict_with_valid_due_date() -> None:
    """Todo.from_dict should accept valid ISO date format (YYYY-MM-DD)."""
    data = {"id": 1, "text": "Buy milk", "done": False, "due_date": "2025-12-31"}
    todo = Todo.from_dict(data)
    assert todo.due_date == "2025-12-31"


def test_todo_from_dict_rejects_invalid_date_format() -> None:
    """Todo.from_dict should reject invalid date formats."""
    invalid_dates = [
        "not-a-date",
        "12-31-2025",  # US format instead of ISO
        "2025/12/31",  # slashes instead of dashes
        "25-12-31",  # missing century
        "2025-13-01",  # invalid month
        "2025-12-32",  # invalid day
        "2025-02-30",  # invalid day for February
        "",  # empty string
    ]

    for invalid_date in invalid_dates:
        data = {"id": 1, "text": "Buy milk", "done": False, "due_date": invalid_date}
        with pytest.raises(ValueError, match=r"Invalid.*due_date"):
            Todo.from_dict(data)


def test_todo_from_dict_rejects_non_string_due_date() -> None:
    """Todo.from_dict should reject non-string due_date values."""
    invalid_types = [
        123,
        123.45,
        True,
        False,
        {"date": "2025-12-31"},
        ["2025-12-31"],
    ]

    for invalid_value in invalid_types:
        data = {"id": 1, "text": "Buy milk", "done": False, "due_date": invalid_value}
        with pytest.raises(ValueError, match=r"Invalid.*due_date"):
            Todo.from_dict(data)


def test_todo_from_dict_accepts_none_due_date() -> None:
    """Todo.from_dict should accept None for due_date."""
    data = {"id": 1, "text": "Buy milk", "done": False, "due_date": None}
    todo = Todo.from_dict(data)
    assert todo.due_date is None


def test_formatter_includes_due_date_in_output() -> None:
    """TodoFormatter should include due_date in formatted output."""
    todo = Todo(id=1, text="Buy milk", due_date="2025-12-31")
    result = TodoFormatter.format_todo(todo)
    assert "2025-12-31" in result


def test_formatter_marks_overdue_task() -> None:
    """TodoFormatter should mark tasks past their due date."""
    # Create a todo with a due date in the past
    past_date = "2020-01-01"
    todo = Todo(id=1, text="Buy milk", due_date=past_date)
    result = TodoFormatter.format_todo(todo)
    # Should contain an OVERDUE indicator
    assert "OVERDUE" in result


def test_formatter_does_not_mark_future_task() -> None:
    """TodoFormatter should not mark tasks with future due dates."""
    future_date = "2099-12-31"
    todo = Todo(id=1, text="Buy milk", due_date=future_date)
    result = TodoFormatter.format_todo(todo)
    # Should NOT contain OVERDUE indicator
    assert "OVERDUE" not in result


def test_formatter_does_not_mark_task_without_due_date() -> None:
    """TodoFormatter should not mark tasks without a due date."""
    todo = Todo(id=1, text="Buy milk")
    result = TodoFormatter.format_todo(todo)
    # Should NOT contain OVERDUE indicator
    assert "OVERDUE" not in result


def test_formatter_handles_today_as_not_overdue() -> None:
    """TodoFormatter should not mark tasks due today as OVERDUE."""
    # Use today's date in ISO format
    today = datetime.now(UTC).date().isoformat()
    todo = Todo(id=1, text="Buy milk", due_date=today)
    result = TodoFormatter.format_todo(todo)
    # Should NOT contain OVERDUE indicator
    assert "OVERDUE" not in result
