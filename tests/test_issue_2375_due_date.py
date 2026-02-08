"""Tests for Todo due_date field (Issue #2375).

These tests verify that:
1. Todo has optional due_date field that accepts ISO date string
2. set_due_date(date: str) method validates and sets due_date, updates updated_at
3. from_dict handles due_date gracefully (missing or invalid values)
4. TodoFormatter shows due date when present (e.g., '[ ]   1 Buy milk (due: 2025-12-31)')
"""

from __future__ import annotations

import pytest

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_todo_has_due_date_field() -> None:
    """Todo should have optional due_date field that accepts ISO date string."""
    todo = Todo(id=1, text="buy milk", due_date="2025-12-31")
    assert todo.due_date == "2025-12-31"


def test_todo_due_date_defaults_to_none() -> None:
    """Todo due_date should default to None when not provided."""
    todo = Todo(id=1, text="buy milk")
    assert todo.due_date is None


def test_set_due_date_with_valid_iso_date() -> None:
    """set_due_date should accept valid ISO date string and update updated_at."""
    todo = Todo(id=1, text="buy milk")
    original_updated_at = todo.updated_at

    todo.set_due_date("2025-12-31")
    assert todo.due_date == "2025-12-31"
    assert todo.updated_at >= original_updated_at


def test_set_due_date_with_invalid_date_raises_value_error() -> None:
    """set_due_date should raise ValueError for invalid date format."""
    todo = Todo(id=1, text="buy milk")

    with pytest.raises(ValueError, match="Invalid ISO date format"):
        todo.set_due_date("not-a-date")

    with pytest.raises(ValueError, match="Invalid ISO date format"):
        todo.set_due_date("2025/12/31")  # Wrong separator


def test_set_due_date_with_iso_datetime_raises_value_error() -> None:
    """set_due_date should accept only YYYY-MM-DD date format, not full datetime."""
    todo = Todo(id=1, text="buy milk")

    # Full ISO datetime should be rejected
    with pytest.raises(ValueError, match="Invalid ISO date format"):
        todo.set_due_date("2025-12-31T23:59:59Z")


def test_from_dict_with_due_date_present() -> None:
    """from_dict should parse due_date correctly when present."""
    data = {
        "id": 1,
        "text": "buy milk",
        "done": False,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "due_date": "2025-12-31",
    }
    todo = Todo.from_dict(data)
    assert todo.due_date == "2025-12-31"


def test_from_dict_without_due_date_sets_none() -> None:
    """from_dict should set due_date to None when not present."""
    data = {
        "id": 1,
        "text": "buy milk",
        "done": False,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }
    todo = Todo.from_dict(data)
    assert todo.due_date is None


def test_from_dict_with_invalid_due_date_sets_none() -> None:
    """from_dict should handle invalid due_date gracefully by setting to None."""
    data = {
        "id": 1,
        "text": "buy milk",
        "done": False,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "due_date": "invalid-date",
    }
    todo = Todo.from_dict(data)
    # Invalid due_date should be treated as None
    assert todo.due_date is None


def test_to_dict_includes_due_date() -> None:
    """to_dict should include due_date in the output."""
    todo = Todo(id=1, text="buy milk", due_date="2025-12-31")
    data = todo.to_dict()
    assert data.get("due_date") == "2025-12-31"


def test_to_dict_with_none_due_date() -> None:
    """to_dict should include due_date as None when not set."""
    todo = Todo(id=1, text="buy milk")
    data = todo.to_dict()
    assert data.get("due_date") is None


def test_format_todo_displays_due_date_when_present() -> None:
    """TodoFormatter should display due date when present."""
    todo = Todo(id=1, text="Buy milk", due_date="2025-12-31")
    result = TodoFormatter.format_todo(todo)
    assert "(due: 2025-12-31)" in result


def test_format_todo_without_due_date() -> None:
    """TodoFormatter should not show due date when not present."""
    todo = Todo(id=1, text="Buy milk")
    result = TodoFormatter.format_todo(todo)
    # Should not contain "(due:" when due_date is None
    assert "(due:" not in result


def test_set_due_date_with_empty_string_clears_due_date() -> None:
    """set_due_date with empty string should clear the due_date."""
    todo = Todo(id=1, text="buy milk", due_date="2025-12-31")

    todo.set_due_date("")
    assert todo.due_date is None


def test_set_due_date_with_none_clears_due_date() -> None:
    """set_due_date with None should clear the due_date."""
    todo = Todo(id=1, text="buy milk", due_date="2025-12-31")

    todo.set_due_date(None)
    assert todo.due_date is None
