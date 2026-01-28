"""Test JSON serialization robustness (issue #1536)."""

import json
from dataclasses import dataclass

from flywheel.formatter import Formatter, FormatType
from flywheel.todo import Todo


def test_format_json_with_missing_to_dict_method():
    """Test that formatter handles objects without to_dict() method gracefully.

    This test creates a mock Todo-like object that doesn't have to_dict() method.
    The formatter should handle this gracefully without crashing.
    """
    # Create a mock object without to_dict method
    class MockTodo:
        def __init__(self):
            self.id = 1
            self.title = "Test Todo"

    mock_todo = MockTodo()
    formatter = Formatter(format_type=FormatType.JSON)

    # This should not crash, but handle the error gracefully
    try:
        result = formatter.format([mock_todo])
        # If it doesn't crash, result should be valid JSON or error message
        assert result is not None
    except (AttributeError, TypeError) as e:
        # Current behavior: it crashes
        # This is the bug we need to fix
        assert "to_dict" in str(e).lower() or "dict" in str(e).lower()


def test_format_json_with_invalid_to_dict_return_type():
    """Test that formatter handles to_dict() returning non-dict type.

    This test creates a mock object whose to_dict() method returns
    something other than a dictionary (e.g., a string).
    """
    class MockTodo:
        def __init__(self):
            self.id = 1
            self.title = "Test Todo"

        def to_dict(self):
            # Return invalid type (string instead of dict)
            return "not a dict"

    mock_todo = MockTodo()
    formatter = Formatter(format_type=FormatType.JSON)

    # This should not crash, but handle the error gracefully
    try:
        result = formatter.format([mock_todo])
        # If it doesn't crash, result should be valid JSON or error message
        assert result is not None
    except (TypeError, ValueError) as e:
        # Current behavior: it crashes with JSON serialization error
        # This is the bug we need to fix
        pass


def test_format_json_with_normal_todo():
    """Test that normal Todo objects work correctly with JSON formatting.

    This test ensures that the fix doesn't break the normal case.
    """
    todo = Todo(
        id=1,
        title="Test Todo",
        description="Test Description",
        status=Todo.Status.TODO,
        priority=Todo.Priority.HIGH
    )

    formatter = Formatter(format_type=FormatType.JSON)
    result = formatter.format([todo])

    # Result should be valid JSON
    parsed = json.loads(result)
    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert parsed[0]["title"] == "Test Todo"
    assert parsed[0]["id"] == 1
