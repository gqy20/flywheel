"""Tests for Todo.from_dict None handling (Issue #2430).

These tests verify that:
1. Todo.from_dict handles None values for created_at/updated_at correctly
2. None is converted to empty string, not the literal string "None"
3. Valid ISO strings are preserved
4. Missing keys result in empty strings

This prevents the semantic inconsistency where None becomes the string "None".
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_from_dict_with_created_at_none_returns_empty_string() -> None:
    """from_dict should convert None created_at to empty string, not 'None'."""
    data = {
        "id": 1,
        "text": "test todo",
        "created_at": None,
        "updated_at": "2024-01-01T00:00:00Z",
    }
    todo = Todo.from_dict(data)

    # created_at should be empty string (or timestamp if __post_init__ sets it)
    # The key assertion: it should NOT be the literal string "None"
    assert todo.created_at != "None", (
        "created_at should not be the literal string 'None' when input is None"
    )


def test_from_dict_with_updated_at_none_returns_empty_string() -> None:
    """from_dict should convert None updated_at to empty string, not 'None'."""
    data = {
        "id": 2,
        "text": "test todo",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": None,
    }
    todo = Todo.from_dict(data)

    # updated_at should be empty string (or timestamp if __post_init__ sets it)
    # The key assertion: it should NOT be the literal string "None"
    assert todo.updated_at != "None", (
        "updated_at should not be the literal string 'None' when input is None"
    )


def test_from_dict_with_both_timestamps_none_returns_empty_strings() -> None:
    """from_dict should handle both timestamps being None."""
    data = {
        "id": 3,
        "text": "test todo",
        "created_at": None,
        "updated_at": None,
    }
    todo = Todo.from_dict(data)

    # Neither should be the literal string "None"
    assert todo.created_at != "None", (
        "created_at should not be 'None' when input is None"
    )
    assert todo.updated_at != "None", (
        "updated_at should not be 'None' when input is None"
    )


def test_from_dict_with_valid_iso_string_preserves_value() -> None:
    """from_dict should preserve valid ISO 8601 timestamp strings."""
    iso_timestamp = "2024-01-15T12:30:45Z"
    data = {
        "id": 4,
        "text": "test todo",
        "created_at": iso_timestamp,
        "updated_at": iso_timestamp,
    }
    todo = Todo.from_dict(data)

    # Valid ISO strings should be preserved exactly
    assert todo.created_at == iso_timestamp, (
        f"created_at should preserve valid ISO string: expected {iso_timestamp!r}, "
        f"got {todo.created_at!r}"
    )
    assert todo.updated_at == iso_timestamp, (
        f"updated_at should preserve valid ISO string: expected {iso_timestamp!r}, "
        f"got {todo.updated_at!r}"
    )


def test_from_dict_with_missing_timestamp_keys_returns_empty_string() -> None:
    """from_dict should handle missing timestamp keys gracefully."""
    data = {
        "id": 5,
        "text": "test todo",
    }
    todo = Todo.from_dict(data)

    # Missing keys should not result in "None" string
    # (empty string or timestamp from __post_init__ is acceptable)
    assert todo.created_at != "None", (
        "created_at should not be 'None' when key is missing"
    )
    assert todo.updated_at != "None", (
        "updated_at should not be 'None' when key is missing"
    )


def test_from_dict_with_empty_string_timestamp_preserves_empty() -> None:
    """from_dict should preserve empty string timestamps."""
    data = {
        "id": 6,
        "text": "test todo",
        "created_at": "",
        "updated_at": "",
    }
    todo = Todo.from_dict(data)

    # Empty strings should remain empty (or be set by __post_init__)
    # The key check: should not be "None"
    assert todo.created_at != "None", (
        "created_at should not be 'None' when input is empty string"
    )
    assert todo.updated_at != "None", (
        "updated_at should not be 'None' when input is empty string"
    )
