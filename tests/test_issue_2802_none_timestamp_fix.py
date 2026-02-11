"""Tests for None timestamp handling (Issue #2802).

These tests verify that:
1. created_at=None results in empty string, not 'None'
2. updated_at=None results in empty string, not 'None'
3. Both timestamps None results in empty strings
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_from_dict_handles_none_created_at() -> None:
    """created_at=None should result in empty string, not 'None'."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": None})
    assert todo.created_at == "", f"Expected empty string, got {todo.created_at!r}"


def test_todo_from_dict_handles_none_updated_at() -> None:
    """updated_at=None should result in empty string, not 'None'."""
    todo = Todo.from_dict({"id": 1, "text": "test", "updated_at": None})
    assert todo.updated_at == "", f"Expected empty string, got {todo.updated_at!r}"


def test_todo_from_dict_handles_both_none_timestamps() -> None:
    """Both timestamps None should result in empty strings."""
    todo = Todo.from_dict({"id": 1, "text": "test", "created_at": None, "updated_at": None})
    assert todo.created_at == "", f"Expected empty string for created_at, got {todo.created_at!r}"
    assert todo.updated_at == "", f"Expected empty string for updated_at, got {todo.updated_at!r}"


def test_todo_from_dict_missing_timestamps_defaults_empty() -> None:
    """Missing timestamp fields should default to empty strings."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.created_at == "", f"Expected empty string for created_at, got {todo.created_at!r}"
    assert todo.updated_at == "", f"Expected empty string for updated_at, got {todo.updated_at!r}"
