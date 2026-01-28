"""Test for issue #1776 - truncated code syntax error.

This test verifies that the from_dict method properly validates
due_date format and provides clear error messages.
"""

import pytest
from flywheel.todo import Todo


def test_from_dict_invalid_due_date_format():
    """Test that invalid due_date format raises ValueError with clear message."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "due_date": "invalid-date-format"
    }

    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict(data)

    assert "Invalid ISO 8601 date format" in str(exc_info.value)
    assert "due_date" in str(exc_info.value)


def test_from_dict_valid_due_date():
    """Test that valid ISO 8601 due_date is accepted."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "due_date": "2026-01-14T10:30:00"
    }

    todo = Todo.from_dict(data)
    assert todo.due_date == "2026-01-14T10:30:00"


def test_from_dict_complete_instance():
    """Test that from_dict creates complete Todo instance."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "description": "Test Description",
        "status": "todo",
        "priority": "high",
        "due_date": "2026-01-14T10:30:00",
        "created_at": "2026-01-14T09:00:00",
        "completed_at": None,
        "tags": ["tag1", "tag2"]
    }

    todo = Todo.from_dict(data)

    assert todo.id == 1
    assert todo.title == "Test Todo"
    assert todo.description == "Test Description"
    assert todo.status.value == "todo"
    assert todo.priority.value == "high"
    assert todo.due_date == "2026-01-14T10:30:00"
    assert todo.created_at == "2026-01-14T09:00:00"
    assert todo.completed_at is None
    assert todo.tags == ["tag1", "tag2"]
