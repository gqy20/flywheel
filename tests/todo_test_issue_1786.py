"""Tests for issue #1786 - Verify todo.py is not truncated."""

import pytest
from flywheel.todo import Todo


def test_todo_from_dict_with_invalid_due_date_format():
    """Test that from_dict properly validates ISO 8601 date format.

    This test verifies that the code is not truncated and properly
    raises ValueError with a complete error message for invalid dates.
    (Issue #1786)
    """
    data = {
        "id": 1,
        "title": "Test Todo",
        "due_date": "invalid-date-format"
    }

    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict(data)

    # Verify the error message is complete (not truncated)
    error_msg = str(exc_info.value)
    assert "Invalid ISO 8601 date format for 'due_date'" in error_msg
    assert "'invalid-date-format'" in error_msg


def test_todo_from_dict_with_valid_due_date():
    """Test that from_dict accepts valid ISO 8601 dates.

    This test verifies the validation logic works correctly.
    (Issue #1786)
    """
    data = {
        "id": 1,
        "title": "Test Todo",
        "due_date": "2026-01-15T10:30:00"
    }

    todo = Todo.from_dict(data)
    assert todo.due_date == "2026-01-15T10:30:00"


def test_todo_module_imports_successfully():
    """Test that the todo module can be imported without syntax errors.

    This verifies the file is not truncated. (Issue #1786)
    """
    # If this import works, the file syntax is valid and not truncated
    from flywheel import todo
    assert hasattr(todo, 'Todo')
    assert hasattr(todo, '_sanitize_text')
