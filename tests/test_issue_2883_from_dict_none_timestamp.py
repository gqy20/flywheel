"""Tests for Todo.from_dict handling None timestamp values (Issue #2883).

These tests verify that:
1. None values for created_at/updated_at are converted to empty strings, not 'None'
2. Falsy but valid values (0, False) are handled correctly
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_from_dict_with_none_timestamps_converts_to_empty_string() -> None:
    """Bug #2883: None timestamp values should become empty strings, not 'None'."""
    todo = Todo.from_dict({
        'id': 1,
        'text': 'test',
        'created_at': None,
        'updated_at': None,
    })

    # None should convert to empty string, NOT the string 'None'
    assert todo.created_at == '', f"Expected empty string for created_at, got {todo.created_at!r}"
    assert todo.updated_at == '', f"Expected empty string for updated_at, got {todo.updated_at!r}"

    # Explicitly check we don't have the 'None' string bug
    assert todo.created_at != 'None', "created_at should not be the string 'None'"
    assert todo.updated_at != 'None', "updated_at should not be the string 'None'"


def test_from_dict_with_none_created_at_only() -> None:
    """Bug #2883: None for created_at should convert to empty string."""
    todo = Todo.from_dict({
        'id': 1,
        'text': 'test',
        'created_at': None,
        'updated_at': '2025-01-01T00:00:00+00:00',
    })

    assert todo.created_at == '', f"Expected empty string for created_at, got {todo.created_at!r}"
    assert todo.created_at != 'None', "created_at should not be the string 'None'"
    assert todo.updated_at == '2025-01-01T00:00:00+00:00'


def test_from_dict_with_none_updated_at_only() -> None:
    """Bug #2883: None for updated_at should convert to empty string."""
    todo = Todo.from_dict({
        'id': 1,
        'text': 'test',
        'created_at': '2025-01-01T00:00:00+00:00',
        'updated_at': None,
    })

    assert todo.created_at == '2025-01-01T00:00:00+00:00'
    assert todo.updated_at == '', f"Expected empty string for updated_at, got {todo.updated_at!r}"
    assert todo.updated_at != 'None', "updated_at should not be the string 'None'"


def test_from_dict_with_zero_timestamp_values() -> None:
    """Bug #2883: Zero (falsy but valid) timestamps should be handled correctly.

    The issue acceptance criteria specifies that from_dict with created_at=0, updated_at=0
    should verify '0' strings are stored (falsy but valid).
    """
    todo = Todo.from_dict({
        'id': 1,
        'text': 'test',
        'created_at': 0,
        'updated_at': 0,
    })

    # Zero is a falsy value but should be converted to '0' string, not empty string
    assert todo.created_at == '0', f"Expected '0' for created_at, got {todo.created_at!r}"
    assert todo.updated_at == '0', f"Expected '0' for updated_at, got {todo.updated_at!r}"


def test_from_dict_with_missing_timestamps_uses_defaults() -> None:
    """Bug #2883: Missing timestamp fields should use default empty strings."""
    todo = Todo.from_dict({
        'id': 1,
        'text': 'test',
        # created_at and updated_at not provided
    })

    assert todo.created_at == '', f"Expected empty string for created_at, got {todo.created_at!r}"
    assert todo.updated_at == '', f"Expected empty string for updated_at, got {todo.updated_at!r}"


def test_from_dict_with_valid_timestamp_strings_preserves_them() -> None:
    """Bug #2883: Valid timestamp strings should be preserved as-is."""
    timestamp = '2025-01-15T12:30:45+00:00'
    todo = Todo.from_dict({
        'id': 1,
        'text': 'test',
        'created_at': timestamp,
        'updated_at': timestamp,
    })

    assert todo.created_at == timestamp
    assert todo.updated_at == timestamp
