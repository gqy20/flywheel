"""Tests for Todo due_date field (Issue #2375).

These tests verify that:
1. Todo has optional due_date field that accepts ISO date string
2. set_due_date(date: str) method validates and sets due_date, updates updated_at
3. from_dict handles due_date gracefully (missing or invalid values)
4. TodoFormatter shows due date when present
"""

from __future__ import annotations

import pytest

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_todo_init_with_due_date() -> None:
    """Todo.__init__ should accept and store due_date field."""
    todo = Todo(id=1, text="buy milk", done=False, due_date="2025-12-31")
    assert todo.due_date == "2025-12-31"


def test_todo_init_without_due_date() -> None:
    """Todo.__init__ should default due_date to None when not provided."""
    todo = Todo(id=1, text="buy milk", done=False)
    assert todo.due_date is None


def test_set_due_date_with_valid_iso_date() -> None:
    """set_due_date should accept valid ISO date string and update updated_at."""
    todo = Todo(id=1, text="buy milk", done=False)
    original_updated_at = todo.updated_at

    todo.set_due_date("2025-12-31")
    assert todo.due_date == "2025-12-31"
    assert todo.updated_at != original_updated_at


def test_set_due_date_with_invalid_date() -> None:
    """set_due_date should raise ValueError for invalid date format."""
    todo = Todo(id=1, text="buy milk", done=False)

    with pytest.raises(ValueError, match="Invalid ISO date format"):
        todo.set_due_date("not-a-date")


def test_set_due_date_to_none() -> None:
    """set_due_date should accept None to clear the due date."""
    todo = Todo(id=1, text="buy milk", done=False, due_date="2025-12-31")
    original_updated_at = todo.updated_at

    todo.set_due_date(None)
    assert todo.due_date is None
    assert todo.updated_at != original_updated_at


def test_from_dict_with_due_date() -> None:
    """Todo.from_dict should parse due_date when present."""
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


def test_from_dict_without_due_date() -> None:
    """Todo.from_dict should set due_date to None when not present."""
    data = {
        "id": 1,
        "text": "buy milk",
        "done": False,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }
    todo = Todo.from_dict(data)
    assert todo.due_date is None


def test_from_dict_with_invalid_due_date() -> None:
    """Todo.from_dict should handle invalid due_date gracefully."""
    data = {
        "id": 1,
        "text": "buy milk",
        "done": False,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "due_date": "invalid-date",
    }
    todo = Todo.from_dict(data)
    # Invalid due_date should be ignored/set to None
    assert todo.due_date is None


def test_to_dict_includes_due_date() -> None:
    """Todo.to_dict should include due_date when present."""
    todo = Todo(id=1, text="buy milk", done=False, due_date="2025-12-31")
    data = todo.to_dict()
    assert data["due_date"] == "2025-12-31"


def test_to_dict_includes_due_date_when_none() -> None:
    """Todo.to_dict should include due_date as None when not set."""
    todo = Todo(id=1, text="buy milk", done=False)
    data = todo.to_dict()
    assert data.get("due_date") is None


def test_format_todo_displays_due_date() -> None:
    """TodoFormatter.format_todo should display due date when present."""
    todo = Todo(id=1, text="buy milk", done=False, due_date="2025-12-31")
    result = TodoFormatter.format_todo(todo)
    assert "(due: 2025-12-31)" in result


def test_format_todo_without_due_date() -> None:
    """TodoFormatter.format_todo should not show due date when None."""
    todo = Todo(id=1, text="buy milk", done=False)
    result = TodoFormatter.format_todo(todo)
    assert "(due:" not in result
