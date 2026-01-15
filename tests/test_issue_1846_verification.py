"""Verification tests for Issue #1846 - False positive detection.

This test suite verifies that the code in src/flywheel/todo.py is complete
and the from_dict method works correctly, especially the due_date validation
that was reported as truncated.

Issue #1846 claimed that line 236 had a truncated f-string:
    raise ValueError(f"Invalid ISO 8601 date format for 'due_date': '{due_

However, the actual code at line 261 is complete:
    raise ValueError(f"Invalid ISO 8601 date format for 'due_date': '{due_date}'")
"""

import pytest
from datetime import datetime
from flywheel.todo import Todo, Status, Priority


def test_from_dict_with_valid_due_date():
    """Test that from_dict correctly handles valid due_date."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "description": "Test description",
        "status": "todo",
        "priority": "medium",
        "due_date": "2026-01-15T10:30:00",
        "tags": ["test", "verification"]
    }
    todo = Todo.from_dict(data)
    assert todo.due_date == "2026-01-15T10:30:00"


def test_from_dict_with_invalid_due_date_format():
    """Test that from_dict correctly raises ValueError for invalid due_date format.

    This test specifically verifies the line that was reported as truncated.
    """
    data = {
        "id": 1,
        "title": "Test Todo",
        "due_date": "invalid-date-format"
    }
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict(data)
    assert "Invalid ISO 8601 date format for 'due_date'" in str(exc_info.value)
    assert "invalid-date-format" in str(exc_info.value)


def test_from_dict_with_all_optional_fields():
    """Test that from_dict handles all optional fields including created_at and completed_at."""
    data = {
        "id": 1,
        "title": "Complete Todo",
        "description": "Full description",
        "status": "in_progress",
        "priority": "high",
        "due_date": "2026-12-31T23:59:59",
        "created_at": "2026-01-01T00:00:00",
        "completed_at": "2026-01-15T12:00:00",
        "tags": ["work", "urgent"]
    }
    todo = Todo.from_dict(data)
    assert todo.id == 1
    assert todo.title == "Complete Todo"
    assert todo.status == Status.IN_PROGRESS
    assert todo.priority == Priority.HIGH
    assert todo.due_date == "2026-12-31T23:59:59"
    assert todo.created_at == "2026-01-01T00:00:00"
    assert todo.completed_at == "2026-01-15T12:00:00"
    assert todo.tags == ["work", "urgent"]


def test_from_dict_with_invalid_created_at_format():
    """Test that from_dict validates created_at ISO 8601 format."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "created_at": "not-a-date"
    }
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict(data)
    assert "Invalid ISO 8601 date format for 'created_at'" in str(exc_info.value)


def test_from_dict_with_invalid_completed_at_format():
    """Test that from_dict validates completed_at ISO 8601 format."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "completed_at": "invalid"
    }
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict(data)
    assert "Invalid ISO 8601 date format for 'completed_at'" in str(exc_info.value)


def test_from_dict_with_non_string_tags():
    """Test that from_dict validates all tags are strings."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "tags": ["valid", 123, "also-valid"]
    }
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict(data)
    assert "All items in 'tags' must be str" in str(exc_info.value)


def test_from_dict_round_trip():
    """Test that to_dict and from_dict are inverse operations."""
    original = Todo(
        id=42,
        title="Round Trip Test",
        description="Testing serialization round trip",
        status=Status.DONE,
        priority=Priority.LOW,
        due_date="2026-06-15T14:30:00",
        tags=["test", "round-trip"]
    )
    data = original.to_dict()
    restored = Todo.from_dict(data)
    assert restored.id == original.id
    assert restored.title == original.title
    assert restored.description == original.description
    assert restored.status == original.status
    assert restored.priority == original.priority
    assert restored.due_date == original.due_date
    assert restored.tags == original.tags


def test_file_syntax_is_valid():
    """Test that the todo.py file can be imported without syntax errors.

    If this test passes, it proves the file is complete and has no
    truncated strings or syntax errors as claimed in issue #1846.
    """
    from flywheel.todo import Todo, _sanitize_text, Priority, Status
    # If we got here, the file is syntactically valid
    assert True
