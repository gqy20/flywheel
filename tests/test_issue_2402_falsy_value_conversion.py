"""Tests for falsy value conversion bug in Todo.from_dict (Issue #2402).

These tests verify that:
1. Numeric 0 is preserved in created_at/updated_at fields
2. Boolean False is preserved in created_at/updated_at fields
3. Empty string is still used when field is missing

The bug was: str(data.get('created_at') or '') which silently converts
falsy values (0, False) to empty string.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_from_dict_preserves_numeric_zero_created_at() -> None:
    """Todo.from_dict should preserve numeric 0 as '0' string in created_at."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": 0})
    # The numeric 0 should be converted to string "0", not empty string ""
    assert todo.created_at == "0"


def test_todo_from_dict_preserves_numeric_zero_updated_at() -> None:
    """Todo.from_dict should preserve numeric 0 as '0' string in updated_at."""
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": 0})
    # The numeric 0 should be converted to string "0", not empty string ""
    assert todo.updated_at == "0"


def test_todo_from_dict_preserves_boolean_false_created_at() -> None:
    """Todo.from_dict should preserve boolean False as 'False' string in created_at."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": False})
    # The boolean False should be converted to string "False", not empty string ""
    assert todo.created_at == "False"


def test_todo_from_dict_preserves_boolean_false_updated_at() -> None:
    """Todo.from_dict should preserve boolean False as 'False' string in updated_at."""
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": False})
    # The boolean False should be converted to string "False", not empty string ""
    assert todo.updated_at == "False"


def test_todo_from_dict_uses_empty_string_when_created_at_missing() -> None:
    """Todo.from_dict should use empty string when created_at is missing."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    # When field is missing, it should default to empty string
    # Then __post_init__ will replace it with current timestamp
    assert todo.created_at != ""  # __post_init__ sets it to current time


def test_todo_from_dict_uses_empty_string_when_updated_at_missing() -> None:
    """Todo.from_dict should use empty string when updated_at is missing."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    # When field is missing, it should default to empty string
    # Then __post_init__ will replace it with created_at value
    assert todo.updated_at != ""  # __post_init__ sets it to created_at


def test_todo_from_dict_preserves_both_falsy_timestamps() -> None:
    """Todo.from_dict should preserve both falsy timestamps when provided."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": 0,
        "updated_at": False
    })
    assert todo.created_at == "0"
    assert todo.updated_at == "False"
