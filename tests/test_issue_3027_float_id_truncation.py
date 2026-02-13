"""Tests for float id validation in Todo.from_dict (Issue #3027).

These tests verify that:
1. Float id values with non-zero fractional parts raise ValueError
2. Float id values with zero fractional part (1.0) are accepted and converted to int
3. Integer id values still work correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_float_id_with_fractional_part() -> None:
    """Todo.from_dict should reject float id values with non-zero fractional part."""
    with pytest.raises(ValueError, match=r"'id'.*integer|fractional"):
        Todo.from_dict({"id": 3.5, "text": "task"})


def test_todo_from_dict_rejects_negative_float_id_with_fractional_part() -> None:
    """Todo.from_dict should reject negative float id values with non-zero fractional part."""
    with pytest.raises(ValueError, match=r"'id'.*integer|fractional"):
        Todo.from_dict({"id": -1.5, "text": "task"})


def test_todo_from_dict_accepts_float_id_with_zero_fractional_part() -> None:
    """Todo.from_dict should accept float id values like 1.0 (zero fractional part)."""
    todo = Todo.from_dict({"id": 1.0, "text": "task"})
    assert todo.id == 1
    assert isinstance(todo.id, int)


def test_todo_from_dict_accepts_integer_id() -> None:
    """Todo.from_dict should still accept integer id values."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1


def test_todo_from_dict_accepts_large_float_with_zero_fractional() -> None:
    """Todo.from_dict should accept large float id values with zero fractional part."""
    todo = Todo.from_dict({"id": 1000000.0, "text": "task"})
    assert todo.id == 1000000
