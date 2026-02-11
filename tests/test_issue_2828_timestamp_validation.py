"""Tests for timestamp field validation in from_dict (Issue #2828).

These tests verify that created_at and updated_at fields:
1. Reject non-string types like dict/list that could cause serialization issues
2. Accept None as empty string default
3. Accept valid ISO timestamp strings
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_dict_created_at() -> None:
    """Todo.from_dict should reject dict for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": {}})


def test_todo_from_dict_rejects_list_created_at() -> None:
    """Todo.from_dict should reject list for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": []})


def test_todo_from_dict_rejects_dict_updated_at() -> None:
    """Todo.from_dict should reject dict for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": {}})


def test_todo_from_dict_rejects_list_updated_at() -> None:
    """Todo.from_dict should reject list for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": []})


def test_todo_from_dict_accepts_none_created_at() -> None:
    """Todo.from_dict should accept None for 'created_at' and auto-fill timestamp."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": None})
    # __post_init__ fills empty timestamps with current ISO time
    assert todo.created_at != ""
    assert "T" in todo.created_at  # Basic ISO format check


def test_todo_from_dict_accepts_none_updated_at() -> None:
    """Todo.from_dict should accept None for 'updated_at' and auto-fill timestamp."""
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": None})
    # __post_init__ fills empty timestamps with created_at value
    assert todo.updated_at != ""
    assert "T" in todo.updated_at  # Basic ISO format check


def test_todo_from_dict_accepts_valid_iso_timestamp() -> None:
    """Todo.from_dict should accept valid ISO timestamp strings."""
    iso_ts = "2024-01-01T00:00:00+00:00"
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": iso_ts, "updated_at": iso_ts})
    assert todo.created_at == iso_ts
    assert todo.updated_at == iso_ts


def test_todo_from_dict_accepts_empty_string_timestamp() -> None:
    """Todo.from_dict should accept empty string for timestamp fields (auto-filled by __post_init__)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": "", "updated_at": ""})
    # __post_init__ fills empty timestamps with current ISO time
    assert todo.created_at != ""
    assert todo.updated_at != ""
    assert "T" in todo.created_at  # Basic ISO format check
