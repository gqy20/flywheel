"""Tests for issue #1700 - Verify from_dict handles completed_at and tags correctly."""

import pytest
from datetime import datetime
from flywheel.todo import Todo


def test_from_dict_with_completed_at():
    """Test from_dict properly validates completed_at field."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "completed_at": "2025-01-14T10:30:00",
    }

    todo = Todo.from_dict(data)

    assert todo.completed_at == "2025-01-14T10:30:00"


def test_from_dict_with_invalid_completed_at():
    """Test from_dict rejects invalid completed_at format."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "completed_at": "invalid-date",
    }

    with pytest.raises(ValueError, match="Invalid ISO 8601 date format"):
        Todo.from_dict(data)


def test_from_dict_with_tags():
    """Test from_dict properly handles tags field."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "tags": ["urgent", "backend"],
    }

    todo = Todo.from_dict(data)

    assert todo.tags == ["urgent", "backend"]


def test_from_dict_with_empty_tags():
    """Test from_dict sanitizes and removes empty tags."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "tags": ["valid", "", "  ", "also-valid"],
    }

    todo = Todo.from_dict(data)

    assert todo.tags == ["valid", "also-valid"]


def test_from_dict_with_all_fields():
    """Test from_dict with completed_at and tags together."""
    data = {
        "id": 1,
        "title": "Complete Task",
        "description": "A test task",
        "status": "done",
        "priority": "high",
        "due_date": "2025-12-31T23:59:59",
        "created_at": "2025-01-01T00:00:00",
        "completed_at": "2025-01-14T10:30:00",
        "tags": ["completed", "tested"],
    }

    todo = Todo.from_dict(data)

    assert todo.id == 1
    assert todo.title == "Complete Task"
    assert todo.description == "A test task"
    assert todo.status.value == "done"
    assert todo.priority.value == "high"
    assert todo.due_date == "2025-12-31T23:59:59"
    assert todo.created_at == "2025-01-01T00:00:00"
    assert todo.completed_at == "2025-01-14T10:30:00"
    assert todo.tags == ["completed", "tested"]


def test_from_dict_default_tags():
    """Test from_dict uses default empty list when tags not provided."""
    data = {
        "id": 1,
        "title": "Test Todo",
    }

    todo = Todo.from_dict(data)

    assert todo.tags == []


def test_from_dict_invalid_tags_type():
    """Test from_dict rejects non-list tags."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "tags": "not-a-list",
    }

    with pytest.raises(ValueError, match="Field 'tags' must be list"):
        Todo.from_dict(data)


def test_from_dict_invalid_tag_item_type():
    """Test from_dict rejects non-string items in tags."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "tags": ["valid", 123, "also-valid"],
    }

    with pytest.raises(ValueError, match="All items in 'tags' must be str"):
        Todo.from_dict(data)
