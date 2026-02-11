"""Tests for Todo.from_dict None timestamp handling (Issue #2856).

These tests verify that:
1. Explicit None values for created_at/updated_at become empty strings
2. Missing created_at/updated_at keys become empty strings
3. Empty strings remain empty strings
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_from_dict_with_explicit_none_created_at() -> None:
    """Todo.from_dict should convert explicit None for created_at to empty string, not 'None' string."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": None})
    assert todo.created_at == "", f"Expected empty string, got {todo.created_at!r}"


def test_todo_from_dict_with_explicit_none_updated_at() -> None:
    """Todo.from_dict should convert explicit None for updated_at to empty string, not 'None' string."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": None})
    assert todo.updated_at == "", f"Expected empty string, got {todo.updated_at!r}"


def test_todo_from_dict_with_both_none_timestamps() -> None:
    """Todo.from_dict should convert explicit None for both timestamps to empty strings."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": None,
        "updated_at": None
    })
    assert todo.created_at == "", f"Expected empty string, got {todo.created_at!r}"
    assert todo.updated_at == "", f"Expected empty string, got {todo.updated_at!r}"


def test_todo_from_dict_with_missing_timestamps() -> None:
    """Todo.from_dict should handle missing created_at/updated_at keys gracefully."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    # Missing keys should result in empty strings (which then get timestamp in __post_init__)
    # The key is that they shouldn't be the string "None"
    assert todo.created_at != "None", "created_at should not be 'None' string"
    assert todo.updated_at != "None", "updated_at should not be 'None' string"


def test_todo_from_dict_with_empty_string_timestamps() -> None:
    """Todo.from_dict should preserve empty strings for timestamps."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": "",
        "updated_at": ""
    })
    assert todo.created_at == ""
    assert todo.updated_at == ""
