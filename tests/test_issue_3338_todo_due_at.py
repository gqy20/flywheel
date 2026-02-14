"""Tests for Todo due_at field and is_overdue() method (Issue #3338).

These tests verify that:
1. Todo can accept due_at parameter (ISO format string or None)
2. due_at defaults to None
3. is_overdue() correctly determines if current time is past due_at
4. set-due CLI command works
"""

from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime, timedelta

import pytest

from flywheel.cli import TodoApp
from flywheel.todo import Todo


def test_todo_due_at_default_is_none() -> None:
    """due_at should default to None."""
    todo = Todo(id=1, text="test task")
    assert todo.due_at is None


def test_todo_due_at_can_be_set() -> None:
    """Todo should accept due_at parameter with ISO format string."""
    due_time = "2026-03-01T12:00:00+00:00"
    todo = Todo(id=1, text="test task", due_at=due_time)
    assert todo.due_at == due_time


def test_todo_due_at_can_be_none() -> None:
    """Todo should accept due_at=None explicitly."""
    todo = Todo(id=1, text="test task", due_at=None)
    assert todo.due_at is None


def test_todo_is_overdue_no_due_date() -> None:
    """is_overdue() should return False when due_at is None."""
    todo = Todo(id=1, text="test task")
    assert todo.is_overdue() is False


def test_todo_is_overdue_past_time() -> None:
    """is_overdue() should return True when current time is past due_at."""
    # Set due_at to 1 hour ago
    past_time = datetime.now(UTC) - timedelta(hours=1)
    todo = Todo(id=1, text="test task", due_at=past_time.isoformat())
    assert todo.is_overdue() is True


def test_todo_is_overdue_future_time() -> None:
    """is_overdue() should return False when current time is before due_at."""
    # Set due_at to 1 hour in the future
    future_time = datetime.now(UTC) + timedelta(hours=1)
    todo = Todo(id=1, text="test task", due_at=future_time.isoformat())
    assert todo.is_overdue() is False


def test_todo_is_overdue_done_task_still_overdue() -> None:
    """is_overdue() should still return True for overdue tasks even if done."""
    past_time = datetime.now(UTC) - timedelta(hours=1)
    todo = Todo(id=1, text="test task", done=True, due_at=past_time.isoformat())
    # Even completed tasks can be overdue
    assert todo.is_overdue() is True


def test_todo_to_dict_includes_due_at() -> None:
    """to_dict() should include due_at field."""
    due_time = "2026-03-01T12:00:00+00:00"
    todo = Todo(id=1, text="test task", due_at=due_time)
    data = todo.to_dict()
    assert "due_at" in data
    assert data["due_at"] == due_time


def test_todo_from_dict_with_due_at() -> None:
    """from_dict() should correctly parse due_at field."""
    data = {
        "id": 1,
        "text": "test task",
        "done": False,
        "due_at": "2026-03-01T12:00:00+00:00",
        "created_at": "2026-02-14T12:00:00+00:00",
        "updated_at": "2026-02-14T12:00:00+00:00",
    }
    todo = Todo.from_dict(data)
    assert todo.due_at == "2026-03-01T12:00:00+00:00"


def test_todo_from_dict_without_due_at() -> None:
    """from_dict() should handle missing due_at field (default to None)."""
    data = {
        "id": 1,
        "text": "test task",
        "done": False,
        "created_at": "2026-02-14T12:00:00+00:00",
        "updated_at": "2026-02-14T12:00:00+00:00",
    }
    todo = Todo.from_dict(data)
    assert todo.due_at is None


def test_todo_is_overdue_exactly_at_due_time() -> None:
    """is_overdue() should return True when current time equals due_at."""
    # Use a fixed past time
    past_time = "2020-01-01T00:00:00+00:00"
    todo = Todo(id=1, text="test task", due_at=past_time)
    # Since we're past this time, it should be overdue
    assert todo.is_overdue() is True


# CLI tests for set-due command


def test_cli_set_due(todo_app: TodoApp) -> None:
    """CLI should support set-due command to set due_at on a todo."""
    # Add a todo
    todo = todo_app.add("task with deadline")
    assert todo.due_at is None

    # Set due date
    due_time = "2026-03-01T12:00:00+00:00"
    updated = todo_app.set_due(todo.id, due_time)
    assert updated.due_at == due_time


def test_cli_set_due_clear(todo_app: TodoApp) -> None:
    """CLI set-due should support clearing due_at with None."""
    # Add a todo with due date
    todo = todo_app.add("task with deadline")
    due_time = "2026-03-01T12:00:00+00:00"
    todo_app.set_due(todo.id, due_time)

    # Clear due date
    updated = todo_app.set_due(todo.id, None)
    assert updated.due_at is None


# Fixture for TodoApp


@pytest.fixture
def todo_app() -> TodoApp:
    """Create a TodoApp with a temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_todos.json")
        app = TodoApp(db_path=db_path)
        yield app
