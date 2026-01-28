"""Test input validation for Todo model."""

import pytest
from flywheel.todo import Todo


class TestTitleValidation:
    """Test title input sanitization."""

    def test_title_cannot_be_empty_string(self):
        """Empty title should raise ValueError."""
        with pytest.raises(ValueError, match="Title cannot be empty"):
            Todo.from_dict({
                "id": 1,
                "title": "",
            })

    def test_title_cannot_be_whitespace_only(self):
        """Whitespace-only title should raise ValueError."""
        with pytest.raises(ValueError, match="Title cannot be empty"):
            Todo.from_dict({
                "id": 1,
                "title": "   ",
            })

    def test_title_must_be_stripped(self):
        """Title should be stripped of leading/trailing whitespace."""
        todo = Todo.from_dict({
            "id": 1,
            "title": "  Valid Title  ",
        })
        assert todo.title == "Valid Title"

    def test_title_minimum_length(self):
        """Title after stripping must have at least 1 character."""
        with pytest.raises(ValueError, match="Title cannot be empty"):
            Todo.from_dict({
                "id": 1,
                "title": "\t\n",
            })

    def test_title_maximum_length(self):
        """Title should not exceed 200 characters."""
        long_title = "a" * 201
        with pytest.raises(ValueError, match="Title too long"):
            Todo.from_dict({
                "id": 1,
                "title": long_title,
            })

    def test_title_exactly_max_length(self):
        """Title of exactly 200 characters should be accepted."""
        valid_title = "a" * 200
        todo = Todo.from_dict({
            "id": 1,
            "title": valid_title,
        })
        assert todo.title == valid_title


class TestDescriptionValidation:
    """Test description input sanitization."""

    def test_description_can_be_empty_string(self):
        """Empty description should be accepted."""
        todo = Todo.from_dict({
            "id": 1,
            "title": "Test",
            "description": "",
        })
        assert todo.description == ""

    def test_description_must_be_stripped(self):
        """Description should be stripped of leading/trailing whitespace."""
        todo = Todo.from_dict({
            "id": 1,
            "title": "Test",
            "description": "  Valid Description  ",
        })
        assert todo.description == "Valid Description"

    def test_description_maximum_length(self):
        """Description should not exceed 5000 characters."""
        long_description = "a" * 5001
        with pytest.raises(ValueError, match="Description too long"):
            Todo.from_dict({
                "id": 1,
                "title": "Test",
                "description": long_description,
            })

    def test_description_exactly_max_length(self):
        """Description of exactly 5000 characters should be accepted."""
        valid_description = "a" * 5000
        todo = Todo.from_dict({
            "id": 1,
            "title": "Test",
            "description": valid_description,
        })
        assert todo.description == valid_description
