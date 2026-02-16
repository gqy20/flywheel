"""Tests for Todo due_date field and is_overdue() method (Issue #3765).

These tests verify that:
1. Todo instances support an optional due_date field (default empty string)
2. is_overdue() correctly determines if current time is past due_date
3. from_dict/to_dict correctly handle due_date field
"""

from __future__ import annotations

from datetime import UTC, datetime

from flywheel.todo import Todo


def test_todo_has_due_date_field_with_default_empty() -> None:
    """Todo should have a due_date field that defaults to empty string."""
    todo = Todo(id=1, text="task")
    assert hasattr(todo, "due_date")
    assert todo.due_date == ""


def test_todo_can_set_due_date() -> None:
    """Todo should accept due_date during initialization."""
    todo = Todo(id=1, text="task", due_date="2025-01-01T00:00:00")
    assert todo.due_date == "2025-01-01T00:00:00"


def test_is_overdue_returns_true_for_past_date() -> None:
    """is_overdue() should return True when due_date is in the past."""
    todo = Todo(id=1, text="task", due_date="2025-01-01T00:00:00")
    assert todo.is_overdue() is True


def test_is_overdue_returns_false_for_future_date() -> None:
    """is_overdue() should return False when due_date is in the future."""
    todo = Todo(id=1, text="task", due_date="2099-12-31T23:59:59")
    assert todo.is_overdue() is False


def test_is_overdue_returns_false_when_no_due_date() -> None:
    """is_overdue() should return False when due_date is empty (no deadline)."""
    todo = Todo(id=1, text="task")
    assert todo.is_overdue() is False


def test_to_dict_includes_due_date() -> None:
    """to_dict should include the due_date field."""
    todo = Todo(id=1, text="task", due_date="2025-06-15T12:00:00")
    d = todo.to_dict()
    assert "due_date" in d
    assert d["due_date"] == "2025-06-15T12:00:00"


def test_to_dict_includes_empty_due_date() -> None:
    """to_dict should include due_date even when empty."""
    todo = Todo(id=1, text="task")
    d = todo.to_dict()
    assert "due_date" in d
    assert d["due_date"] == ""


def test_from_dict_handles_due_date() -> None:
    """from_dict should correctly parse due_date from dict."""
    todo = Todo.from_dict({"id": 1, "text": "task", "due_date": "2025-06-15T12:00:00"})
    assert todo.due_date == "2025-06-15T12:00:00"


def test_from_dict_handles_missing_due_date() -> None:
    """from_dict should use empty string as default when due_date is missing."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.due_date == ""


def test_is_overdue_compares_with_current_time() -> None:
    """is_overdue should compare due_date against current UTC time."""
    # Create a todo with due_date 1 second in the past
    past_time = datetime.now(UTC).isoformat()
    todo_past = Todo(id=1, text="overdue task", due_date=past_time)
    # Even if just created, past time should be overdue
    assert todo_past.is_overdue() is True

    # Create a todo with empty due_date
    todo_no_due = Todo(id=2, text="no deadline")
    assert todo_no_due.is_overdue() is False
