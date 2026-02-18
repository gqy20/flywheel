"""Tests for Todo.id positive integer validation (Issue #4284).

These tests verify that:
1. Todo.from_dict rejects negative id values
2. Todo.from_dict rejects zero id value (consistent with positive-only IDs)
3. Todo.from_dict accepts positive id values
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match=r"positive|'id'.*>= ?1|invalid.*'id'"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject zero id value (IDs should be positive)."""
    with pytest.raises(ValueError, match=r"positive|'id'.*>= ?1|invalid.*'id'"):
        Todo.from_dict({"id": 0, "text": "task"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1

    # Also test larger positive ids
    todo2 = Todo.from_dict({"id": 42, "text": "another task"})
    assert todo2.id == 42
