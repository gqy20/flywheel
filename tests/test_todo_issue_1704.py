"""Tests for Todo completed_at field (issue #1704)."""

from datetime import datetime
import pytest
from flywheel.todo import Todo, Status, Priority


def test_completed_at_field_in_to_dict():
    """Test that completed_at field is properly serialized to dict."""
    completed_time = "2026-01-14T10:30:00"
    todo = Todo(
        id=1,
        title="Test todo",
        completed_at=completed_time
    )
    data = todo.to_dict()

    assert "completed_at" in data
    assert data["completed_at"] == completed_time


def test_completed_at_field_in_from_dict():
    """Test that completed_at field is properly deserialized from dict."""
    completed_time = "2026-01-14T10:30:00"
    data = {
        "id": 1,
        "title": "Test todo",
        "completed_at": completed_time
    }
    todo = Todo.from_dict(data)

    assert todo.completed_at == completed_time


def test_completed_at_validates_iso_format():
    """Test that completed_at validates ISO 8601 format."""
    data = {
        "id": 1,
        "title": "Test todo",
        "completed_at": "invalid-date"
    }

    with pytest.raises(ValueError, match="Invalid ISO 8601 date format"):
        Todo.from_dict(data)


def test_completed_at_accepts_none():
    """Test that completed_at can be None."""
    data = {
        "id": 1,
        "title": "Test todo",
        "completed_at": None
    }
    todo = Todo.from_dict(data)

    assert todo.completed_at is None


def test_completed_at_accepts_valid_iso_datetime():
    """Test that completed_at accepts valid ISO 8601 datetime."""
    completed_time = datetime.now().isoformat()
    data = {
        "id": 1,
        "title": "Test todo",
        "completed_at": completed_time
    }
    todo = Todo.from_dict(data)

    assert todo.completed_at == completed_time


def test_completed_at_round_trip():
    """Test that completed_at survives round trip through to_dict and from_dict."""
    original_completed = "2026-01-14T10:30:45.123456"
    original_todo = Todo(
        id=1,
        title="Test todo",
        description="Test description",
        completed_at=original_completed
    )

    # Convert to dict and back
    data = original_todo.to_dict()
    restored_todo = Todo.from_dict(data)

    assert restored_todo.completed_at == original_completed
