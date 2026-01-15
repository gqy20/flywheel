"""Test Todo.from_dict method with all fields."""

import pytest
from flywheel.todo import Todo, Status, Priority


def test_from_dict_with_all_fields():
    """Test that from_dict correctly handles all fields including due_date, created_at, completed_at, and tags."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "description": "Test Description",
        "status": "in_progress",
        "priority": "high",
        "due_date": "2026-01-15T10:00:00",
        "created_at": "2026-01-10T08:00:00",
        "completed_at": "2026-01-15T12:00:00",
        "tags": ["work", "urgent"]
    }

    todo = Todo.from_dict(data)

    assert todo.id == 1
    assert todo.title == "Test Todo"
    assert todo.description == "Test Description"
    assert todo.status == Status.IN_PROGRESS
    assert todo.priority == Priority.HIGH
    assert todo.due_date == "2026-01-15T10:00:00"
    assert todo.created_at == "2026-01-10T08:00:00"
    assert todo.completed_at == "2026-01-15T12:00:00"
    assert todo.tags == ["work", "urgent"]


def test_from_dict_with_minimal_fields():
    """Test that from_dict works with only required fields."""
    data = {
        "id": 1,
        "title": "Minimal Todo"
    }

    todo = Todo.from_dict(data)

    assert todo.id == 1
    assert todo.title == "Minimal Todo"
    assert todo.description is None
    assert todo.status == Status.TODO
    assert todo.priority == Priority.MEDIUM
    assert todo.due_date is None
    assert todo.completed_at is None
    assert todo.tags == []
    assert todo.created_at is not None  # Should be auto-generated


def test_from_dict_invalid_date_format():
    """Test that from_dict raises ValueError for invalid date format."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "due_date": "invalid-date"
    }

    with pytest.raises(ValueError, match="Invalid ISO 8601 date format"):
        Todo.from_dict(data)


def test_from_dict_invalid_status():
    """Test that from_dict raises ValueError for invalid status."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "status": "invalid_status"
    }

    with pytest.raises(ValueError, match="Invalid status value"):
        Todo.from_dict(data)


def test_from_dict_to_dict_roundtrip():
    """Test that to_dict and from_dict maintain data integrity."""
    original = Todo(
        id=1,
        title="Roundtrip Test",
        description="Testing roundtrip",
        status=Status.DONE,
        priority=Priority.LOW,
        due_date="2026-01-15T10:00:00",
        created_at="2026-01-10T08:00:00",
        completed_at="2026-01-15T12:00:00",
        tags=["test", "roundtrip"]
    )

    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.id == original.id
    assert restored.title == original.title
    assert restored.description == original.description
    assert restored.status == original.status
    assert restored.priority == original.priority
    assert restored.due_date == original.due_date
    assert restored.created_at == original.created_at
    assert restored.completed_at == original.completed_at
    assert restored.tags == original.tags
