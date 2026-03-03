"""Tests for Todo due_date field (Issue #6886).

These tests verify that:
1. Todo has optional due_date field (ISO format string or None)
2. set_due_date() method updates due_date and updated_at
3. is_overdue property returns True when due_date < now and not done
4. from_dict() parses ISO format due_date strings
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from flywheel.todo import Todo


class TestTodoDueDateField:
    """Tests for due_date field existence and initialization."""

    def test_todo_has_due_date_field(self) -> None:
        """Todo dataclass should include optional due_date field."""
        todo = Todo(id=1, text="test task")
        # Should have due_date attribute, defaulting to None
        assert hasattr(todo, "due_date")
        assert todo.due_date is None

    def test_todo_with_due_date(self) -> None:
        """Todo can be created with a due_date."""
        due = "2025-12-31T23:59:59+00:00"
        todo = Todo(id=1, text="task with deadline", due_date=due)
        assert todo.due_date == due

    def test_todo_to_dict_includes_due_date(self) -> None:
        """to_dict() should include due_date field."""
        todo = Todo(id=1, text="test", due_date="2025-06-01T12:00:00+00:00")
        d = todo.to_dict()
        assert "due_date" in d
        assert d["due_date"] == "2025-06-01T12:00:00+00:00"

    def test_todo_to_dict_includes_due_date_none(self) -> None:
        """to_dict() should include due_date field even when None."""
        todo = Todo(id=1, text="test")
        d = todo.to_dict()
        assert "due_date" in d
        assert d["due_date"] is None


class TestTodoSetDueDate:
    """Tests for set_due_date() method."""

    def test_set_due_date_updates_field(self) -> None:
        """set_due_date() should update the due_date field."""
        todo = Todo(id=1, text="test")
        assert todo.due_date is None

        due = "2025-12-31T23:59:59+00:00"
        todo.set_due_date(due)
        assert todo.due_date == due

    def test_set_due_date_updates_updated_at(self) -> None:
        """set_due_date() should update the updated_at timestamp."""
        todo = Todo(id=1, text="test")
        original_updated_at = todo.updated_at

        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)

        todo.set_due_date("2025-12-31T23:59:59+00:00")
        assert todo.updated_at > original_updated_at

    def test_set_due_date_can_clear(self) -> None:
        """set_due_date(None) should clear the due_date."""
        todo = Todo(id=1, text="test", due_date="2025-12-31T23:59:59+00:00")
        assert todo.due_date is not None

        todo.set_due_date(None)
        assert todo.due_date is None


class TestTodoIsOverdue:
    """Tests for is_overdue property."""

    def test_is_overdue_true_for_past_due_date(self) -> None:
        """Todo with past due_date returns is_overdue=True."""
        past_due = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        todo = Todo(id=1, text="overdue task", due_date=past_due, done=False)
        assert todo.is_overdue is True

    def test_is_overdue_false_for_future_due_date(self) -> None:
        """Todo with future due_date returns is_overdue=False."""
        future_due = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        todo = Todo(id=1, text="future task", due_date=future_due, done=False)
        assert todo.is_overdue is False

    def test_is_overdue_false_for_completed_todo(self) -> None:
        """Completed todo with past due_date returns is_overdue=False."""
        past_due = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        todo = Todo(id=1, text="completed overdue task", due_date=past_due, done=True)
        assert todo.is_overdue is False

    def test_is_overdue_false_when_no_due_date(self) -> None:
        """Todo without due_date returns is_overdue=False."""
        todo = Todo(id=1, text="no deadline", done=False)
        assert todo.is_overdue is False

    def test_is_overdue_false_for_due_now(self) -> None:
        """Todo with due_date in the immediate future should not be overdue."""
        # Use 1 second in the future to avoid race conditions
        future_due = (datetime.now(UTC) + timedelta(seconds=1)).isoformat()
        todo = Todo(id=1, text="due now", due_date=future_due, done=False)
        # Due in the immediate future should not be overdue
        assert todo.is_overdue is False


class TestTodoFromDictDueDate:
    """Tests for from_dict() parsing due_date."""

    def test_from_dict_parses_due_date_string(self) -> None:
        """from_dict() should parse ISO format due_date strings."""
        data = {
            "id": 1,
            "text": "test",
            "due_date": "2025-12-31T23:59:59+00:00",
        }
        todo = Todo.from_dict(data)
        assert todo.due_date == "2025-12-31T23:59:59+00:00"

    def test_from_dict_handles_missing_due_date(self) -> None:
        """from_dict() should handle missing due_date (default to None)."""
        data = {"id": 1, "text": "test"}
        todo = Todo.from_dict(data)
        assert todo.due_date is None

    def test_from_dict_handles_null_due_date(self) -> None:
        """from_dict() should handle explicit null due_date."""
        data = {"id": 1, "text": "test", "due_date": None}
        todo = Todo.from_dict(data)
        assert todo.due_date is None

    def test_from_dict_roundtrip(self) -> None:
        """from_dict(to_dict()) should preserve due_date."""
        original = Todo(id=1, text="test", due_date="2025-06-01T12:00:00+00:00")
        data = original.to_dict()
        restored = Todo.from_dict(data)
        assert restored.due_date == original.due_date


class TestTodoStorageWithDueDate:
    """Tests for storage persistence with due_date."""

    def test_storage_roundtrip_with_due_date(self, tmp_path) -> None:
        """Storage should persist and restore due_date field."""
        from flywheel.storage import TodoStorage

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        todos = [
            Todo(id=1, text="no deadline"),
            Todo(id=2, text="with deadline", due_date="2025-12-31T23:59:59+00:00"),
        ]
        storage.save(todos)

        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].due_date is None
        assert loaded[1].due_date == "2025-12-31T23:59:59+00:00"
