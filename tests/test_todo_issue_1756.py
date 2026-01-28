"""Test to verify Issue #1756 is a false positive.

Issue #1756 claims the code is truncated at line 234 with:
    raise ValueError(f"Invalid ISO 8601 date format for 'due_date': '{due_

This test verifies that:
1. The file is syntactically correct (can be imported)
2. The due_date validation logic works correctly
3. The error message is complete and properly formatted
"""

import pytest
from flywheel.todo import Todo


def test_todo_file_is_complete():
    """Verify the todo.py file is syntactically correct and complete.

    This test checks that:
    - The module can be imported (no SyntaxError)
    - The from_dict method exists and is callable
    - The due_date validation error message is complete
    """
    # Test that invalid due_date raises the expected complete error message
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({
            "id": 1,
            "title": "Test Todo",
            "due_date": "invalid-date-format"
        })

    # Verify the error message is complete and contains the full text
    error_message = str(exc_info.value)
    assert "Invalid ISO 8601 date format for 'due_date':" in error_message
    assert "invalid-date-format" in error_message

    # The error message should be complete, not truncated
    assert error_message.endswith("'") or error_message.endswith("'.")


def test_todo_due_date_validation_with_valid_iso8601():
    """Verify that valid ISO 8601 dates are accepted."""
    todo = Todo.from_dict({
        "id": 1,
        "title": "Test Todo",
        "due_date": "2026-01-14T18:30:00"
    })
    assert todo.due_date == "2026-01-14T18:30:00"


def test_todo_due_date_validation_with_invalid_formats():
    """Verify various invalid date formats are properly rejected with complete error messages."""
    invalid_dates = [
        "not-a-date",
        "2026-13-01",  # Invalid month
        "2026-01-32",  # Invalid day
        "",  # Empty string
    ]

    for invalid_date in invalid_dates:
        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict({
                "id": 1,
                "title": "Test Todo",
                "due_date": invalid_date
            })

        error_message = str(exc_info.value)
        # Verify error message is complete (not truncated)
        assert "Invalid ISO 8601 date format" in error_message
        # Verify the invalid date value is included in the error message
        assert invalid_date in error_message
