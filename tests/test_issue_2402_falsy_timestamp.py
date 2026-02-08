"""Tests for falsy timestamp value handling in from_dict (Issue #2402).

These tests verify that:
1. from_dict with created_at='0' preserves '0' as created_at
2. from_dict with created_at=0 sets created_at to '0' (not empty string)
3. from_dict with missing created_at key defaults to empty string
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_from_dict_preserves_string_zero_timestamp() -> None:
    """from_dict should preserve string '0' as created_at value."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": "0"})
    assert todo.created_at == "0"


def test_todo_from_dict_converts_int_zero_to_string() -> None:
    """from_dict should convert integer 0 to string '0' for created_at."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": 0})
    assert todo.created_at == "0"


def test_todo_from_dict_defaults_missing_timestamp() -> None:
    """from_dict should default to empty string when created_at key is missing."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    # Empty string gets replaced by __post_init__ with current timestamp
    assert todo.created_at != ""


def test_todo_from_dict_preserves_string_zero_updated_at() -> None:
    """from_dict should preserve string '0' as updated_at value."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": "0"})
    assert todo.updated_at == "0"


def test_todo_from_dict_converts_int_zero_to_string_updated_at() -> None:
    """from_dict should convert integer 0 to string '0' for updated_at."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": 0})
    assert todo.updated_at == "0"


def test_todo_from_dict_preserves_false_timestamp() -> None:
    """from_dict should convert False to string 'False' for created_at."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": False})
    assert todo.created_at == "False"
