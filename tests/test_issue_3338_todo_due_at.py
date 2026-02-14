"""Tests for Todo due_at field support (Issue #3338).

These tests verify that:
1. Todo can accept due_at parameter (ISO format string or None)
2. is_overdue() method correctly determines if current time is past due_at
3. Todo supports set_due() method to update due_at
4. from_dict() and to_dict() handle due_at field properly
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from flywheel.todo import Todo


class TestTodoDueAtField:
    """Tests for the due_at field on Todo."""

    def test_todo_due_at_defaults_to_none(self) -> None:
        """Todo.due_at should default to None."""
        todo = Todo(id=1, text="buy milk")
        assert todo.due_at is None

    def test_todo_due_at_accepts_iso_string(self) -> None:
        """Todo.due_at should accept an ISO format string."""
        future_time = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        todo = Todo(id=1, text="buy milk", due_at=future_time)
        assert todo.due_at == future_time


class TestTodoIsOverdue:
    """Tests for the is_overdue() method."""

    def test_todo_is_overdue_true_with_past_time(self) -> None:
        """is_overdue() should return True when due_at is in the past."""
        past_time = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        todo = Todo(id=1, text="overdue task", due_at=past_time)
        assert todo.is_overdue() is True

    def test_todo_is_overdue_false_with_future_time(self) -> None:
        """is_overdue() should return False when due_at is in the future."""
        future_time = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        todo = Todo(id=1, text="future task", due_at=future_time)
        assert todo.is_overdue() is False

    def test_todo_is_overdue_false_when_due_at_is_none(self) -> None:
        """is_overdue() should return False when due_at is None."""
        todo = Todo(id=1, text="no deadline", due_at=None)
        assert todo.is_overdue() is False


class TestTodoSetDue:
    """Tests for the set_due() method."""

    def test_todo_set_due_updates_due_at(self) -> None:
        """set_due() should update the due_at field."""
        todo = Todo(id=1, text="task")
        future_time = (datetime.now(UTC) + timedelta(days=3)).isoformat()
        todo.set_due(future_time)
        assert todo.due_at == future_time

    def test_todo_set_due_updates_updated_at(self) -> None:
        """set_due() should update the updated_at timestamp."""
        todo = Todo(id=1, text="task")
        old_updated_at = todo.updated_at
        future_time = (datetime.now(UTC) + timedelta(days=3)).isoformat()
        todo.set_due(future_time)
        assert todo.updated_at != old_updated_at

    def test_todo_set_due_can_clear_due_at(self) -> None:
        """set_due(None) should clear the due_at field."""
        future_time = (datetime.now(UTC) + timedelta(days=3)).isoformat()
        todo = Todo(id=1, text="task", due_at=future_time)
        assert todo.due_at is not None
        todo.set_due(None)
        assert todo.due_at is None


class TestTodoDueAtSerialization:
    """Tests for serialization/deserialization with due_at."""

    def test_todo_to_dict_includes_due_at(self) -> None:
        """to_dict() should include due_at field."""
        future_time = (datetime.now(UTC) + timedelta(days=3)).isoformat()
        todo = Todo(id=1, text="task", due_at=future_time)
        data = todo.to_dict()
        assert "due_at" in data
        assert data["due_at"] == future_time

    def test_todo_from_dict_with_due_at(self) -> None:
        """from_dict() should correctly parse due_at field."""
        future_time = (datetime.now(UTC) + timedelta(days=3)).isoformat()
        data = {"id": 1, "text": "task", "due_at": future_time}
        todo = Todo.from_dict(data)
        assert todo.due_at == future_time

    def test_todo_from_dict_without_due_at(self) -> None:
        """from_dict() should handle missing due_at field (defaults to None)."""
        data = {"id": 1, "text": "task"}
        todo = Todo.from_dict(data)
        assert todo.due_at is None

    def test_todo_from_dict_with_null_due_at(self) -> None:
        """from_dict() should handle explicit null due_at."""
        data = {"id": 1, "text": "task", "due_at": None}
        todo = Todo.from_dict(data)
        assert todo.due_at is None
