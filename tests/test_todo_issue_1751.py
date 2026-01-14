"""Tests for Todo due_date error message format (issue #1751).

This test verifies that the ValueError raised for invalid due_date format
is correctly formatted with the complete variable name and proper syntax.
"""

import pytest
from flywheel.todo import Todo


def test_due_date_error_message_format():
    """Test that invalid due_date raises ValueError with properly formatted message.

    This test ensures that the error message includes the complete variable name
    and is properly formatted (issue #1751 - verification of false positive).
    """
    data = {
        "id": 1,
        "title": "Test todo",
        "due_date": "invalid-date-format"
    }

    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict(data)

    error_message = str(exc_info.value)
    # Verify the error message is properly formatted
    assert "Invalid ISO 8601 date format for 'due_date':" in error_message
    assert "'invalid-date-format'" in error_message
    # Ensure the message is complete (not truncated)
    assert error_message.endswith("'")
    assert error_message.count("'") >= 4  # At least 2 pairs of quotes


def test_due_date_accepts_valid_iso8601():
    """Test that due_date accepts valid ISO 8601 format."""
    data = {
        "id": 1,
        "title": "Test todo",
        "due_date": "2026-01-14T10:30:00"
    }

    todo = Todo.from_dict(data)
    assert todo.due_date == "2026-01-14T10:30:00"


def test_due_date_accepts_none():
    """Test that due_date can be None."""
    data = {
        "id": 1,
        "title": "Test todo",
        "due_date": None
    }

    todo = Todo.from_dict(data)
    assert todo.due_date is None
