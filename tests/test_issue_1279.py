"""Tests for issue #1279 - Input sanitization for title and description."""

import pytest
from flywheel.todo import Todo


class TestInputSanitization:
    """Test input sanitization for security."""

    def test_title_with_control_characters(self):
        """Title should remove control characters."""
        data = {
            "id": 1,
            "title": "Hello\x00\x01\x02World",
        }
        todo = Todo.from_dict(data)
        # Control characters should be removed
        assert "\x00" not in todo.title
        assert "\x01" not in todo.title
        assert "\x02" not in todo.title
        assert "HelloWorld" == todo.title

    def test_title_with_newline_and_tab(self):
        """Title should remove newline and tab characters."""
        data = {
            "id": 1,
            "title": "Hello\nWorld\tTest",
        }
        todo = Todo.from_dict(data)
        assert "\n" not in todo.title
        assert "\t" not in todo.title
        assert "HelloWorldTest" == todo.title

    def test_title_with_carriage_return(self):
        """Title should remove carriage return characters."""
        data = {
            "id": 1,
            "title": "Hello\r\nWorld",
        }
        todo = Todo.from_dict(data)
        assert "\r" not in todo.title
        assert "\n" not in todo.title
        assert "HelloWorld" == todo.title

    def test_title_with_null_bytes(self):
        """Title should remove null bytes."""
        data = {
            "id": 1,
            "title": "Test\x00\x00\x00Title",
        }
        todo = Todo.from_dict(data)
        assert "\x00" not in todo.title
        assert "TestTitle" == todo.title

    def test_title_with_special_whitespace(self):
        """Title should normalize special whitespace characters."""
        data = {
            "id": 1,
            "title": "Hello\u200b\u200c\u200dWorld",
        }
        todo = Todo.from_dict(data)
        # Zero-width spaces should be removed
        assert "\u200b" not in todo.title
        assert "\u200c" not in todo.title
        assert "\u200d" not in todo.title

    def test_description_with_control_characters(self):
        """Description should remove control characters."""
        data = {
            "id": 1,
            "title": "Test",
            "description": "Desc\x00\x01\x02cription",
        }
        todo = Todo.from_dict(data)
        assert "\x00" not in todo.description
        assert "\x01" not in todo.description
        assert "\x02" not in todo.description
        assert "Description" == todo.description

    def test_description_with_newlines_and_tabs(self):
        """Description should remove newlines and tabs."""
        data = {
            "id": 1,
            "title": "Test",
            "description": "Line1\nLine2\tTabbed",
        }
        todo = Todo.from_dict(data)
        assert "\n" not in todo.description
        assert "\t" not in todo.description
        assert "Line1Line2Tabbed" == todo.description

    def test_description_with_carriage_return(self):
        """Description should remove carriage return characters."""
        data = {
            "id": 1,
            "title": "Test",
            "description": "Desc\r\nription",
        }
        todo = Todo.from_dict(data)
        assert "\r" not in todo.description
        assert "\n" not in todo.description
        assert "Description" == todo.description

    def test_title_with_multiple_control_chars(self):
        """Title should handle multiple control characters."""
        data = {
            "id": 1,
            "title": "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f"
            "\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f",
        }
        todo = Todo.from_dict(data)
        # All control characters should be removed
        assert todo.title == ""
        # Empty after sanitization should raise error
        with pytest.raises(ValueError, match="Title cannot be empty"):
            Todo.from_dict(data)

    def test_description_preserves_normal_content(self):
        """Description should preserve normal text content."""
        data = {
            "id": 1,
            "title": "Test",
            "description": "This is a normal description with normal text.",
        }
        todo = Todo.from_dict(data)
        assert todo.description == "This is a normal description with normal text."

    def test_title_preserves_normal_content(self):
        """Title should preserve normal text content."""
        data = {
            "id": 1,
            "title": "This is a normal title",
        }
        todo = Todo.from_dict(data)
        assert todo.title == "This is a normal title"
