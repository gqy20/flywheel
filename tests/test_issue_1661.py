"""Test for Issue #1661 - Verify Todo.from_dict works correctly with completed_at field."""

import pytest
from flywheel.todo import Todo, Priority, Status


def test_from_dict_with_completed_at():
    """Test that from_dict properly handles completed_at field."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "description": "Test description",
        "status": "done",
        "priority": "high",
        "completed_at": "2024-01-13T10:00:00",
        "tags": ["test", "example"]
    }

    # This should work without errors
    todo = Todo.from_dict(data)

    assert todo.id == 1
    assert todo.title == "Test Todo"
    assert todo.completed_at == "2024-01-13T10:00:00"
    assert todo.status == Status.DONE
    assert todo.priority == Priority.HIGH


def test_from_dict_without_completed_at():
    """Test that from_dict works when completed_at is not provided."""
    data = {
        "id": 2,
        "title": "Another Todo",
        "status": "todo",
    }

    todo = Todo.from_dict(data)

    assert todo.id == 2
    assert todo.title == "Another Todo"
    assert todo.completed_at is None


def test_from_dict_with_invalid_completed_at():
    """Test that from_dict validates completed_at format."""
    data = {
        "id": 3,
        "title": "Invalid Date Todo",
        "completed_at": "invalid-date-format",
    }

    with pytest.raises(ValueError, match="Invalid ISO 8601 date format"):
        Todo.from_dict(data)


def test_todo_to_dict_roundtrip():
    """Test that Todo -> dict -> Todo roundtrip works."""
    original = Todo(
        id=100,
        title="Roundtrip Test",
        description="Testing roundtrip conversion",
        status=Status.IN_PROGRESS,
        priority=Priority.LOW,
        completed_at="2024-01-13T15:30:00",
        tags=["roundtrip", "test"]
    )

    # Convert to dict
    data_dict = original.to_dict()

    # Convert back to Todo
    restored = Todo.from_dict(data_dict)

    # Verify all fields match
    assert restored.id == original.id
    assert restored.title == original.title
    assert restored.description == original.description
    assert restored.status == original.status
    assert restored.priority == original.priority
    assert restored.completed_at == original.completed_at
    assert restored.tags == original.tags
