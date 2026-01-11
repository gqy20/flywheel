"""Test date format validation for issue #1424."""

import pytest
from flywheel.todo import Todo


class TestDateFormatValidation:
    """Test that date strings are validated for ISO 8601 format."""

    def test_invalid_due_date_format_raises_error(self):
        """Test that invalid due_date format raises ValueError."""
        data = {
            "id": 1,
            "title": "Test Todo",
            "due_date": "not-a-valid-date"
        }
        with pytest.raises(ValueError, match="Invalid ISO 8601 date format"):
            Todo.from_dict(data)

    def test_invalid_created_at_format_raises_error(self):
        """Test that invalid created_at format raises ValueError."""
        data = {
            "id": 1,
            "title": "Test Todo",
            "created_at": "2024-13-45"  # Invalid month and day
        }
        with pytest.raises(ValueError, match="Invalid ISO 8601 date format"):
            Todo.from_dict(data)

    def test_invalid_completed_at_format_raises_error(self):
        """Test that invalid completed_at format raises ValueError."""
        data = {
            "id": 1,
            "title": "Test Todo",
            "completed_at": "yesterday"
        }
        with pytest.raises(ValueError, match="Invalid ISO 8601 date format"):
            Todo.from_dict(data)

    def test_valid_due_date_format_accepted(self):
        """Test that valid ISO 8601 due_date is accepted."""
        data = {
            "id": 1,
            "title": "Test Todo",
            "due_date": "2024-12-25"
        }
        todo = Todo.from_dict(data)
        assert todo.due_date == "2024-12-25"

    def test_valid_iso8601_with_time_accepted(self):
        """Test that valid ISO 8601 with time is accepted."""
        data = {
            "id": 1,
            "title": "Test Todo",
            "created_at": "2024-12-25T14:30:00"
        }
        todo = Todo.from_dict(data)
        assert todo.created_at == "2024-12-25T14:30:00"

    def test_none_date_values_accepted(self):
        """Test that None values for date fields are accepted."""
        data = {
            "id": 1,
            "title": "Test Todo",
            "due_date": None,
            "completed_at": None
        }
        todo = Todo.from_dict(data)
        assert todo.due_date is None
        assert todo.completed_at is None

    def test_empty_string_date_rejected(self):
        """Test that empty string for date fields is rejected."""
        data = {
            "id": 1,
            "title": "Test Todo",
            "due_date": ""
        }
        with pytest.raises(ValueError, match="Invalid ISO 8601 date format"):
            Todo.from_dict(data)
