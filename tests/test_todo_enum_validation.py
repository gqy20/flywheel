"""Test enum validation in Todo model."""

import pytest

from flywheel.todo import Todo, Status, Priority


class TestEnumValidation:
    """Test that invalid enum values are properly rejected."""

    def test_from_dict_with_invalid_status_raises_error(self):
        """Test that from_dict raises ValueError for invalid status."""
        data = {
            "id": 1,
            "title": "Test Todo",
            "status": "invalid_status",  # Invalid status value
        }

        with pytest.raises(ValueError, match="Invalid.*status.*invalid_status"):
            Todo.from_dict(data)

    def test_from_dict_with_invalid_priority_raises_error(self):
        """Test that from_dict raises ValueError for invalid priority."""
        data = {
            "id": 1,
            "title": "Test Todo",
            "priority": "invalid_priority",  # Invalid priority value
        }

        with pytest.raises(ValueError, match="Invalid.*priority.*invalid_priority"):
            Todo.from_dict(data)

    def test_from_dict_with_valid_status_succeeds(self):
        """Test that from_dict succeeds with valid status."""
        data = {
            "id": 1,
            "title": "Test Todo",
            "status": "in_progress",
        }

        todo = Todo.from_dict(data)
        assert todo.status == Status.IN_PROGRESS

    def test_from_dict_with_valid_priority_succeeds(self):
        """Test that from_dict succeeds with valid priority."""
        data = {
            "id": 1,
            "title": "Test Todo",
            "priority": "high",
        }

        todo = Todo.from_dict(data)
        assert todo.priority == Priority.HIGH
