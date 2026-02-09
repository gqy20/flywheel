"""Tests for Issue #2430 - from_dict None handling for created_at and updated_at.

These tests verify that:
1. When created_at is None, it should result in empty string (not 'None')
2. When updated_at is None, it should result in empty string (not 'None')
3. Valid ISO format strings are preserved correctly
4. Missing keys are handled the same as None values
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_from_dict_with_none_created_at() -> None:
    """created_at=None should result in empty string, not 'None'."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": None})
    # Due to __post_init__, empty string becomes current ISO timestamp
    # But it should NOT be the string 'None'
    assert todo.created_at != "None"
    assert isinstance(todo.created_at, str)
    # The empty string is handled by __post_init__ to set current time
    # So we just verify it's not the literal 'None' string


def test_from_dict_with_none_updated_at() -> None:
    """updated_at=None should result in empty string, not 'None'."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": None})
    # Due to __post_init__, empty string becomes current ISO timestamp
    # But it should NOT be the string 'None'
    assert todo.updated_at != "None"
    assert isinstance(todo.updated_at, str)


def test_from_dict_with_both_none_timestamps() -> None:
    """Both created_at=None and updated_at=None should not become 'None' strings."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": None,
        "updated_at": None
    })
    assert todo.created_at != "None"
    assert todo.updated_at != "None"


def test_from_dict_preserves_valid_iso_string_created_at() -> None:
    """Valid ISO format string for created_at should be preserved."""
    iso_time = "2024-01-01T00:00:00Z"
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": iso_time})
    assert todo.created_at == iso_time


def test_from_dict_preserves_valid_iso_string_updated_at() -> None:
    """Valid ISO format string for updated_at should be preserved."""
    iso_time = "2024-01-01T12:30:45Z"
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": iso_time})
    assert todo.updated_at == iso_time


def test_from_dict_with_missing_created_at_key() -> None:
    """Missing created_at key should be handled gracefully (not become 'None')."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.created_at != "None"
    # Due to __post_init__, it becomes current ISO timestamp
    assert isinstance(todo.created_at, str)


def test_from_dict_with_missing_updated_at_key() -> None:
    """Missing updated_at key should be handled gracefully (not become 'None')."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.updated_at != "None"
    # Due to __post_init__, it becomes current ISO timestamp
    assert isinstance(todo.updated_at, str)


def test_from_dict_with_empty_string_timestamps() -> None:
    """Empty string for timestamps should be handled gracefully."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": "",
        "updated_at": ""
    })
    assert todo.created_at != "None"
    assert todo.updated_at != "None"
    # Empty strings trigger __post_init__ to set current time
    assert isinstance(todo.created_at, str)
    assert isinstance(todo.updated_at, str)
