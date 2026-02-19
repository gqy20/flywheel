"""Tests for float id truncation bug (Issue #4495).

These tests verify that:
1. Todo.from_dict rejects float ids with non-zero decimal parts (e.g., 1.5)
2. Todo.from_dict rejects float ids even when decimal part is zero (e.g., 1.0)
3. Todo.from_dict still accepts integer ids unchanged

This prevents silent data collision where int(1.5) would silently return 1.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_float_with_nonzero_decimal() -> None:
    """Todo.from_dict should reject float id with non-zero decimal (e.g., 1.5)."""
    with pytest.raises(ValueError, match=r"'id'.*integer|invalid.*'id'"):
        Todo.from_dict({"id": 1.5, "text": "task"})


def test_todo_from_dict_rejects_float_with_zero_decimal() -> None:
    """Todo.from_dict should reject float id even when decimal is zero (e.g., 1.0)."""
    with pytest.raises(ValueError, match=r"'id'.*integer|invalid.*'id'"):
        Todo.from_dict({"id": 1.0, "text": "task"})


def test_todo_from_dict_accepts_integer_id() -> None:
    """Todo.from_dict should still accept valid integer ids."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1
    assert todo.text == "task"


def test_todo_from_dict_accepts_large_integer_id() -> None:
    """Todo.from_dict should accept large integer ids."""
    todo = Todo.from_dict({"id": 999999, "text": "task"})
    assert todo.id == 999999


def test_todo_from_dict_rejects_negative_float_id() -> None:
    """Todo.from_dict should reject negative float ids."""
    with pytest.raises(ValueError, match=r"'id'.*integer|invalid.*'id'"):
        Todo.from_dict({"id": -1.5, "text": "task"})
