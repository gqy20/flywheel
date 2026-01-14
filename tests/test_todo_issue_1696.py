"""Test for Issue #1696 - Verify from_dict method handles completed_at and tags correctly."""

import pytest
from datetime import datetime
from flywheel.todo import Todo, Status, Priority


def test_from_dict_with_completed_at_and_tags():
    """Test that from_dict properly handles completed_at and tags fields."""
    # Create a dictionary with all fields including completed_at and tags
    data = {
        "id": 1,
        "title": "Test Todo",
        "description": "Test Description",
        "status": "done",
        "priority": "high",
        "due_date": "2026-01-15T10:00:00",
        "created_at": "2026-01-14T10:00:00",
        "completed_at": "2026-01-14T12:00:00",
        "tags": ["work", "urgent"]
    }

    # Create Todo from dict
    todo = Todo.from_dict(data)

    # Verify all fields are set correctly
    assert todo.id == 1
    assert todo.title == "Test Todo"
    assert todo.description == "Test Description"
    assert todo.status == Status.DONE
    assert todo.priority == Priority.HIGH
    assert todo.due_date == "2026-01-15T10:00:00"
    assert todo.created_at == "2026-01-14T10:00:00"
    assert todo.completed_at == "2026-01-14T12:00:00"
    assert todo.tags == ["work", "urgent"]


def test_from_dict_without_optional_fields():
    """Test that from_dict works without optional completed_at and tags fields."""
    data = {
        "id": 2,
        "title": "Simple Todo",
    }

    # Create Todo from dict
    todo = Todo.from_dict(data)

    # Verify required fields and defaults
    assert todo.id == 2
    assert todo.title == "Simple Todo"
    assert todo.description is None
    assert todo.status == Status.TODO
    assert todo.priority == Priority.MEDIUM
    assert todo.due_date is None
    assert todo.completed_at is None
    assert todo.tags == []


def test_from_dict_with_empty_tags():
    """Test that from_dict handles empty tags list."""
    data = {
        "id": 3,
        "title": "Todo with empty tags",
        "tags": []
    }

    todo = Todo.from_dict(data)

    assert todo.tags == []


def test_from_dict_sanitizes_tags():
    """Test that from_dict sanitizes tags to remove control characters."""
    data = {
        "id": 4,
        "title": "Todo",
        "tags": ["work\x00", "urgent\t", "  valid  "]
    }

    todo = Todo.from_dict(data)

    # Tags should be sanitized and whitespace trimmed
    assert "work" in todo.tags
    assert "urgent" in todo.tags
    assert "valid" in todo.tags


def test_from_dict_validates_completed_at_format():
    """Test that from_dict validates completed_at is ISO 8601 format."""
    data = {
        "id": 5,
        "title": "Todo",
        "completed_at": "invalid-date"
    }

    with pytest.raises(ValueError, match="Invalid ISO 8601 date format for 'completed_at'"):
        Todo.from_dict(data)


def test_from_dict_validates_tags_type():
    """Test that from_dict validates tags is a list."""
    data = {
        "id": 6,
        "title": "Todo",
        "tags": "not-a-list"
    }

    with pytest.raises(ValueError, match="Field 'tags' must be list"):
        Todo.from_dict(data)
