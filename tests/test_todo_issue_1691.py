"""Tests for Todo.from_dict() method - Issue #1691."""

import pytest
from datetime import datetime
from flywheel.todo import Todo, Status, Priority


def test_from_dict_with_completed_at():
    """Test from_dict correctly handles completed_at field."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "description": "Test description",
        "status": "done",
        "priority": "high",
        "due_date": "2026-01-14T10:00:00",
        "created_at": "2026-01-14T09:00:00",
        "completed_at": "2026-01-14T11:00:00",
        "tags": ["tag1", "tag2"]
    }

    todo = Todo.from_dict(data)

    assert todo.id == 1
    assert todo.title == "Test Todo"
    assert todo.description == "Test description"
    assert todo.status == Status.DONE
    assert todo.priority == Priority.HIGH
    assert todo.due_date == "2026-01-14T10:00:00"
    assert todo.created_at == "2026-01-14T09:00:00"
    assert todo.completed_at == "2026-01-14T11:00:00"
    assert todo.tags == ["tag1", "tag2"]


def test_from_dict_without_completed_at():
    """Test from_dict correctly handles missing completed_at field."""
    data = {
        "id": 2,
        "title": "Test Todo 2",
        "status": "todo"
    }

    todo = Todo.from_dict(data)

    assert todo.id == 2
    assert todo.title == "Test Todo 2"
    assert todo.status == Status.TODO
    assert todo.completed_at is None


def test_from_dict_with_invalid_completed_at_format():
    """Test from_dict rejects invalid ISO 8601 format for completed_at."""
    data = {
        "id": 3,
        "title": "Test Todo 3",
        "completed_at": "invalid-date"
    }

    with pytest.raises(ValueError, match="Invalid ISO 8601 date format for 'completed_at'"):
        Todo.from_dict(data)


def test_from_dict_with_invalid_completed_at_type():
    """Test from_dict rejects non-string completed_at."""
    data = {
        "id": 4,
        "title": "Test Todo 4",
        "completed_at": 12345
    }

    with pytest.raises(ValueError, match="Field 'completed_at' must be str or None"):
        Todo.from_dict(data)
