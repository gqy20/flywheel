"""Tests for 'done' field type validation (Issue #2125).

These tests verify that:
1. Invalid 'done' values (non-boolean, non-0/1 integers) raise ValueError
2. Valid 'done' values (true/false booleans) work correctly
3. Legacy integer values (0/1) are accepted for backwards compatibility
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_truthy_non_boolean_int() -> None:
    """Todo.from_dict should reject non-boolean integers like 2 for 'done' field."""
    with pytest.raises(ValueError, match=r"invalid.*'done'|'done'.*boolean|'done'.*integer"):
        Todo.from_dict({"id": 1, "text": "test", "done": 2})


def test_todo_from_dict_rejects_negative_int() -> None:
    """Todo.from_dict should reject negative integers for 'done' field."""
    with pytest.raises(ValueError, match=r"invalid.*'done'|'done'.*boolean|'done'.*integer"):
        Todo.from_dict({"id": 1, "text": "test", "done": -1})


def test_todo_from_dict_rejects_truthy_string() -> None:
    """Todo.from_dict should reject string 'false' for 'done' field.

    This is a critical bug - 'false' as a string becomes True due to truthiness,
    causing exact opposite of intended behavior.
    """
    with pytest.raises(ValueError, match=r"invalid.*'done'|'done'.*boolean|'done'.*integer"):
        Todo.from_dict({"id": 1, "text": "test", "done": "false"})


def test_todo_from_dict_rejects_any_string() -> None:
    """Todo.from_dict should reject any string for 'done' field."""
    with pytest.raises(ValueError, match=r"invalid.*'done'|'done'.*boolean|'done'.*integer"):
        Todo.from_dict({"id": 1, "text": "test", "done": "true"})


def test_todo_from_dict_rejects_empty_string() -> None:
    """Todo.from_dict should reject empty string for 'done' field."""
    with pytest.raises(ValueError, match=r"invalid.*'done'|'done'.*boolean|'done'.*integer"):
        Todo.from_dict({"id": 1, "text": "test", "done": ""})


def test_todo_from_dict_rejects_list() -> None:
    """Todo.from_dict should reject list for 'done' field."""
    with pytest.raises(ValueError, match=r"invalid.*'done'|'done'.*boolean|'done'.*integer"):
        Todo.from_dict({"id": 1, "text": "test", "done": []})


def test_todo_from_dict_rejects_dict() -> None:
    """Todo.from_dict should reject dict for 'done' field."""
    with pytest.raises(ValueError, match=r"invalid.*'done'|'done'.*boolean|'done'.*integer"):
        Todo.from_dict({"id": 1, "text": "test", "done": {}})


def test_todo_from_dict_accepts_boolean_true() -> None:
    """Todo.from_dict should accept boolean True for 'done' field."""
    todo = Todo.from_dict({"id": 1, "text": "test", "done": True})
    assert todo.done is True


def test_todo_from_dict_accepts_boolean_false() -> None:
    """Todo.from_dict should accept boolean False for 'done' field."""
    todo = Todo.from_dict({"id": 1, "text": "test", "done": False})
    assert todo.done is False


def test_todo_from_dict_accepts_legacy_one() -> None:
    """Todo.from_dict should accept integer 1 for 'done' field (legacy compatibility)."""
    todo = Todo.from_dict({"id": 1, "text": "test", "done": 1})
    assert todo.done is True


def test_todo_from_dict_accepts_legacy_zero() -> None:
    """Todo.from_dict should accept integer 0 for 'done' field (legacy compatibility)."""
    todo = Todo.from_dict({"id": 1, "text": "test", "done": 0})
    assert todo.done is False


def test_todo_from_dict_defaults_to_false_when_missing() -> None:
    """Todo.from_dict should default 'done' to False when field is missing."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.done is False
