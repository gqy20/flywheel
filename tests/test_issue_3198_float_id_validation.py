"""Tests for float id validation in Todo.from_dict (Issue #3198).

These tests verify that:
1. Todo.from_dict rejects float id values with non-zero decimal (e.g., 3.7)
2. Todo.from_dict rejects float id values even with zero decimal (e.g., 3.0)
3. Todo.from_dict continues to accept integer id values
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_float_id_with_decimal() -> None:
    """Todo.from_dict should reject float id values with non-zero decimal (e.g., 3.7)."""
    with pytest.raises(ValueError, match=r"'id' must be an integer|invalid.*'id'"):
        Todo.from_dict({"id": 3.7, "text": "test"})


def test_todo_from_dict_rejects_float_id_whole_number() -> None:
    """Todo.from_dict should reject float id values even with zero decimal (e.g., 3.0)."""
    with pytest.raises(ValueError, match=r"'id' must be an integer|invalid.*'id'"):
        Todo.from_dict({"id": 3.0, "text": "test"})


def test_todo_from_dict_accepts_integer_id() -> None:
    """Todo.from_dict should continue to accept valid integer id values."""
    todo = Todo.from_dict({"id": 5, "text": "test task"})
    assert todo.id == 5
    assert todo.text == "test task"


def test_todo_from_dict_accepts_string_integer_id() -> None:
    """Todo.from_dict should accept string representations of integers for id."""
    todo = Todo.from_dict({"id": "10", "text": "test task"})
    assert todo.id == 10
