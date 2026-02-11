"""Tests for Issue #2856 - Todo.from_dict None handling for timestamps.

This test validates that Todo.from_dict correctly handles None values
for created_at and updated_at fields, converting them to empty strings
rather than the string 'None'.

Note: The issue description claimed there was a bug where None would be
converted to 'None' string, but the actual code str(data.get("created_at") or "")
already handles this correctly due to Python operator precedence:
- None or "" evaluates to "" (empty string)
- str("") evaluates to "" (empty string)

These tests verify this correct behavior and serve as regression protection.

Note: The __post_init__ method automatically fills empty timestamps with
current time, so we test that the value passed from from_dict is properly
converted (to empty string, not 'None' string), not the final object value.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_with_explicit_none_timestamps_becomes_timestamp() -> None:
    """Todo.from_dict with None timestamps should get auto-filled with current time."""
    todo = Todo.from_dict(
        {"id": 1, "text": "test", "created_at": None, "updated_at": None}
    )

    # from_dict correctly converts None to "" (empty string)
    # __post_init__ then fills empty strings with current timestamp
    # The key assertion: created_at should NOT be the string 'None'
    assert todo.created_at != "None", "created_at should not be 'None' string"
    assert todo.updated_at != "None", "updated_at should not be 'None' string"

    # Verify they were filled with actual timestamps (non-empty, ISO format-ish)
    assert todo.created_at != "", "Empty None should be filled with timestamp by __post_init__"
    assert todo.updated_at != "", "Empty None should be filled with timestamp by __post_init__"
    assert "T" in todo.created_at, "Should be ISO format timestamp"


def test_todo_from_dict_with_missing_timestamp_keys_becomes_timestamp() -> None:
    """Todo.from_dict with missing timestamp keys should get auto-filled with current time."""
    todo = Todo.from_dict({"id": 1, "text": "test"})

    # Missing keys result in empty string via data.get() default and or ""
    # __post_init__ fills empty strings with current timestamp
    assert todo.created_at != "None", "created_at should not be 'None' string"
    assert todo.updated_at != "None", "updated_at should not be 'None' string"

    assert todo.created_at != "", "Empty string should be filled with timestamp by __post_init__"
    assert todo.updated_at != "", "Empty string should be filled with timestamp by __post_init__"


def test_todo_from_dict_with_partial_none_timestamps() -> None:
    """Todo.from_dict should handle None for one timestamp and not the other."""
    # created_at is None (becomes empty, then filled by __post_init__)
    # updated_at has a value (preserved)
    todo = Todo.from_dict(
        {
            "id": 1,
            "text": "test",
            "created_at": None,
            "updated_at": "2024-01-01T00:00:00Z",
        }
    )

    # created_at should be filled (not 'None' string, not empty)
    assert todo.created_at != "None", "created_at should not be 'None' string"
    assert todo.created_at != "", "Empty created_at should be filled by __post_init__"

    # updated_at should preserve the provided valid timestamp
    assert todo.updated_at == "2024-01-01T00:00:00Z", "Valid timestamp should be preserved"
    assert todo.updated_at != "None", "updated_at should not be 'None' string"


def test_todo_from_dict_preserves_valid_timestamp_strings() -> None:
    """Todo.from_dict should preserve valid ISO timestamp strings."""
    valid_timestamp = "2024-01-15T12:30:45Z"
    todo = Todo.from_dict(
        {"id": 1, "text": "test", "created_at": valid_timestamp, "updated_at": valid_timestamp}
    )

    assert todo.created_at == valid_timestamp
    assert todo.updated_at == valid_timestamp


def test_todo_from_dict_empty_string_timestamps_becomes_timestamp() -> None:
    """Todo.from_dict with empty string timestamps should get auto-filled."""
    todo = Todo.from_dict(
        {"id": 1, "text": "test", "created_at": "", "updated_at": ""}
    )

    # Empty strings are filled by __post_init__ with current timestamp
    # Key assertion: should not be 'None' string
    assert todo.created_at != "None", "created_at should not be 'None' string"
    assert todo.updated_at != "None", "updated_at should not be 'None' string"
    assert todo.created_at != "", "Empty string should be filled by __post_init__"
    assert todo.updated_at != "", "Empty string should be filled by __post_init__"


def test_python_operator_precedence_verification() -> None:
    """Verify that the expression str(data.get("created_at") or "") handles None correctly.

    This test documents the Python operator precedence that makes the current code correct:
    - or has LOWER precedence than function call
    - So str(None or "") is parsed as str((None or "")) not (str(None)) or ""
    - None or "" evaluates to "" (empty string because None is falsy)
    - str("") evaluates to "" (empty string)
    """
    # Simulate the exact code path
    data = {"created_at": None}

    # This is how the current code works
    result = str(data.get("created_at") or "")

    # Verify it produces empty string, not 'None'
    assert result == "", f"Expected empty string, got {repr(result)}"
    assert result != "None", "Should not be 'None' string"
