"""Tests for float id rejection (Issue #3198).

These tests verify that Todo.from_dict rejects float id values that would
lose precision when converted to int, preventing silent id collisions.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_non_integer_float_id() -> None:
    """Todo.from_dict should reject float id values with decimal precision."""
    with pytest.raises(ValueError, match=r"'id'.*integer|'id'.*float"):
        Todo.from_dict({"id": 3.7, "text": "task"})


def test_todo_from_dict_rejects_integer_float_id() -> None:
    """Todo.from_dict should reject all float id values, even integer-valued ones."""
    # Consistent behavior: reject all floats regardless of decimal part
    with pytest.raises(ValueError, match=r"'id'.*integer|'id'.*float"):
        Todo.from_dict({"id": 3.0, "text": "task"})


def test_todo_from_dict_accepts_integer_id() -> None:
    """Todo.from_dict should continue to accept proper integer id values."""
    todo = Todo.from_dict({"id": 3, "text": "task"})
    assert todo.id == 3
