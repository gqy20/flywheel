"""Tests for Todo.from_dict handling None timestamp values (Issue #2883).

These tests verify that:
1. Todo.from_dict with None timestamps doesn't create the string 'None'
2. Valid timestamp values (including falsy ones like 0) are preserved
3. ISO timestamp strings are preserved correctly
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_from_dict_with_none_timestamps_no_none_string() -> None:
    """from_dict should never create the string 'None' from None timestamp values.

    This is the core bug fix: the old code pattern str(data.get()) or "" would
    produce the string 'None' when data.get() returns None.
    """
    data = {"id": 1, "text": "test", "created_at": None, "updated_at": None}
    todo = Todo.from_dict(data)

    # The critical assertion: timestamps should NEVER be the string 'None'
    assert todo.created_at != "None", "created_at should not be the string 'None'"
    assert todo.updated_at != "None", "updated_at should not be the string 'None'"


def test_from_dict_with_zero_timestamp_values() -> None:
    """from_dict should handle falsy but valid timestamp values like 0.

    The fix uses explicit None checking, so 0 is preserved (not treated as falsy).
    """
    data = {"id": 1, "text": "test", "created_at": 0, "updated_at": 0}
    todo = Todo.from_dict(data)

    # 0 should be converted to string '0', not auto-populated by __post_init__
    assert todo.created_at == "0", f"Expected '0', got {todo.created_at!r}"
    assert todo.updated_at == "0", f"Expected '0', got {todo.updated_at!r}"
    assert todo.created_at != "None", "created_at should not be the string 'None'"
    assert todo.updated_at != "None", "updated_at should not be the string 'None'"


def test_from_dict_with_empty_string_timestamps() -> None:
    """from_dict should handle empty string timestamp values.

    Empty strings are falsy, so __post_init__ will auto-populate them with current time.
    But they should NEVER become the string 'None'.
    """
    data = {"id": 1, "text": "test", "created_at": "", "updated_at": ""}
    todo = Todo.from_dict(data)

    # __post_init__ auto-populates empty strings with timestamps
    # But we verify it's never the string 'None'
    assert todo.created_at != "None", "created_at should not be the string 'None'"
    assert todo.updated_at != "None", "updated_at should not be the string 'None'"


def test_from_dict_with_valid_iso_timestamps() -> None:
    """from_dict should preserve valid ISO timestamp strings."""
    iso_time = "2025-02-11T12:00:00+00:00"
    data = {"id": 1, "text": "test", "created_at": iso_time, "updated_at": iso_time}
    todo = Todo.from_dict(data)

    assert todo.created_at == iso_time, f"Expected {iso_time!r}, got {todo.created_at!r}"
    assert todo.updated_at == iso_time, f"Expected {iso_time!r}, got {todo.updated_at!r}"
    assert todo.created_at != "None", "created_at should not be the string 'None'"
    assert todo.updated_at != "None", "updated_at should not be the string 'None'"


def test_from_dict_without_timestamp_fields() -> None:
    """from_dict should work without timestamp fields (defaults apply via __post_init__)."""
    data = {"id": 1, "text": "test"}
    todo = Todo.from_dict(data)

    # __post_init__ will populate timestamps
    # But from_dict should not set them to 'None' string
    assert todo.created_at != "None", "created_at should not be the string 'None'"
    assert todo.updated_at != "None", "updated_at should not be the string 'None'"


def test_from_dict_with_mixed_none_and_valid() -> None:
    """from_dict should handle mixed None and valid timestamp values."""
    iso_time = "2025-02-11T12:00:00+00:00"
    data = {"id": 1, "text": "test", "created_at": None, "updated_at": iso_time}
    todo = Todo.from_dict(data)

    # created_at will be auto-populated by __post_init__ (empty string trigger)
    assert todo.created_at != "None", "created_at should not be the string 'None'"
    # updated_at should be the ISO timestamp
    assert todo.updated_at == iso_time, f"Expected {iso_time!r}, got {todo.updated_at!r}"
    assert todo.updated_at != "None", "updated_at should not be the string 'None'"
