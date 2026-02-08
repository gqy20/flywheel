"""Tests for Todo due_date field (Issue #2375).

These tests verify that:
1. Todo model has optional due_date field
2. set_due_date() method validates ISO dates and updates updated_at
3. from_dict/to_dict handle due_date field correctly
4. TodoFormatter displays due date when present
"""

from __future__ import annotations

import pytest

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_todo_with_due_date_stores_value() -> None:
    """Todo with due_date in __init__ stores value correctly."""
    todo = Todo(id=1, text="buy milk", due_date="2025-12-31")
    assert todo.due_date == "2025-12-31"


def test_todo_without_due_date_defaults_to_none() -> None:
    """Todo without due_date defaults to None."""
    todo = Todo(id=1, text="buy milk")
    assert todo.due_date is None


def test_set_due_date_with_valid_iso_date() -> None:
    """set_due_date with valid ISO date string works."""
    todo = Todo(id=1, text="buy milk")
    todo.set_due_date("2025-12-31")
    assert todo.due_date == "2025-12-31"


def test_set_due_date_with_invalid_date_raises_valueerror() -> None:
    """set_due_date with invalid date raises ValueError."""
    todo = Todo(id=1, text="buy milk")
    with pytest.raises(ValueError, match="Invalid ISO date format"):
        todo.set_due_date("not-a-date")


def test_set_due_date_updates_updated_at() -> None:
    """set_due_date updates updated_at timestamp."""
    todo = Todo(id=1, text="buy milk")
    original_updated_at = todo.updated_at
    # Small delay to ensure timestamp differs
    todo.set_due_date("2025-12-31")
    assert todo.updated_at != original_updated_at


def test_from_dict_with_due_date_parses_correctly() -> None:
    """from_dict with due_date present parses correctly."""
    data = {
        "id": 1,
        "text": "buy milk",
        "done": False,
        "due_date": "2025-12-31",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }
    todo = Todo.from_dict(data)
    assert todo.due_date == "2025-12-31"


def test_from_dict_without_due_date_sets_none() -> None:
    """from_dict without due_date sets None."""
    data = {
        "id": 1,
        "text": "buy milk",
        "done": False,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }
    todo = Todo.from_dict(data)
    assert todo.due_date is None


def test_to_dict_includes_due_date() -> None:
    """to_dict includes due_date field."""
    todo = Todo(id=1, text="buy milk", due_date="2025-12-31")
    data = todo.to_dict()
    assert "due_date" in data
    assert data["due_date"] == "2025-12-31"


def test_to_dict_with_none_due_date() -> None:
    """to_dict includes due_date field even when None."""
    todo = Todo(id=1, text="buy milk")
    data = todo.to_dict()
    assert "due_date" in data
    assert data["due_date"] is None


def test_format_todo_displays_due_date_when_present() -> None:
    """TodoFormatter shows due date when present."""
    todo = Todo(id=1, text="buy milk", due_date="2025-12-31")
    result = TodoFormatter.format_todo(todo)
    assert "(due: 2025-12-31)" in result


def test_format_todo_without_due_date_no_parens() -> None:
    """TodoFormatter without due_date has no '(due: ...)' suffix."""
    todo = Todo(id=1, text="buy milk")
    result = TodoFormatter.format_todo(todo)
    assert "(due:" not in result
