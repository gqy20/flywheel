"""Tests for due_date field (Issue #2348).

These tests verify that:
1. Todo class has optional due_date field (None or ISO date string)
2. Todo.from_dict accepts and validates due_date format
3. TodoFormatter marks overdue tasks with OVERDUE prefix
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_todo_has_due_date_field_default_none() -> None:
    """Todo should have due_date field that defaults to None."""
    todo = Todo(id=1, text="buy milk", done=False)
    assert hasattr(todo, "due_date")
    assert todo.due_date is None


def test_todo_due_date_accepts_iso_date() -> None:
    """Todo should accept ISO format date string for due_date."""
    todo = Todo(id=1, text="buy milk", done=False, due_date="2025-12-31")
    assert todo.due_date == "2025-12-31"


def test_todo_from_dict_with_valid_due_date() -> None:
    """Todo.from_dict should accept valid ISO date string for due_date."""
    data = {
        "id": 1,
        "text": "buy milk",
        "done": False,
        "due_date": "2025-12-31",
    }
    todo = Todo.from_dict(data)
    assert todo.due_date == "2025-12-31"


def test_todo_from_dict_with_none_due_date() -> None:
    """Todo.from_dict should handle None or missing due_date."""
    data = {
        "id": 1,
        "text": "buy milk",
        "done": False,
    }
    todo = Todo.from_dict(data)
    assert todo.due_date is None


def test_todo_from_dict_rejects_invalid_date_format() -> None:
    """Todo.from_dict should reject invalid date formats."""
    data = {
        "id": 1,
        "text": "buy milk",
        "done": False,
        "due_date": "not-a-date",
    }
    with pytest.raises(ValueError, match=r"Invalid.*due_date"):
        Todo.from_dict(data)


def test_todo_from_dict_rejects_invalid_iso_date() -> None:
    """Todo.from_dict should reject non-ISO date strings."""
    data = {
        "id": 1,
        "text": "buy milk",
        "done": False,
        "due_date": "12/31/2025",  # Not ISO format
    }
    with pytest.raises(ValueError, match=r"Invalid.*due_date"):
        Todo.from_dict(data)


def test_todo_to_dict_includes_due_date() -> None:
    """Todo.to_dict should include due_date field."""
    todo = Todo(id=1, text="buy milk", done=False, due_date="2025-12-31")
    data = todo.to_dict()
    assert data["due_date"] == "2025-12-31"


def test_todo_to_dict_with_none_due_date() -> None:
    """Todo.to_dict should include due_date even when None."""
    todo = Todo(id=1, text="buy milk", done=False)
    data = todo.to_dict()
    assert "due_date" in data
    assert data["due_date"] is None


def test_formatter_marks_overdue_tasks() -> None:
    """TodoFormatter should mark overdue tasks with OVERDUE prefix."""
    # Create a todo with a due_date in the past
    past_date = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
    todo = Todo(id=1, text="overdue task", done=False, due_date=past_date)

    result = TodoFormatter.format_todo(todo)
    assert "OVERDUE" in result


def test_formatter_does_not_mark_future_tasks() -> None:
    """TodoFormatter should not mark future tasks as OVERDUE."""
    # Create a todo with a due_date in the future
    future_date = (datetime.now(UTC) + timedelta(days=7)).strftime("%Y-%m-%d")
    todo = Todo(id=1, text="future task", done=False, due_date=future_date)

    result = TodoFormatter.format_todo(todo)
    assert "OVERDUE" not in result


def test_formatter_does_not_mark_tasks_without_due_date() -> None:
    """TodoFormatter should not mark tasks without due_date as OVERDUE."""
    todo = Todo(id=1, text="task without due date", done=False)
    result = TodoFormatter.format_todo(todo)
    assert "OVERDUE" not in result


def test_formatter_does_not_mark_completed_overdue_tasks() -> None:
    """TodoFormatter should not mark completed tasks as OVERDUE even if past due_date."""
    past_date = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
    todo = Todo(id=1, text="completed overdue task", done=True, due_date=past_date)

    result = TodoFormatter.format_todo(todo)
    # Completed tasks should not show OVERDUE
    assert "OVERDUE" not in result


def test_formatter_shows_due_date_in_output() -> None:
    """TodoFormatter should include due_date in the formatted output."""
    todo = Todo(id=1, text="task with due date", done=False, due_date="2025-12-31")
    result = TodoFormatter.format_todo(todo)
    assert "2025-12-31" in result
