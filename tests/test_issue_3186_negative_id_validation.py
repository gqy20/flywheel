"""Tests for negative id validation (Issue #3186).

These tests verify that:
1. Todo.from_dict rejects negative id values
2. Todo.from_dict rejects id=0 (ids should start from 1)
3. Todo.from_dict accepts positive id values
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match=r"positive|invalid.*'id'|'id'.*positive"):
        Todo.from_dict({"id": -1, "text": "test task"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0 (ids should start from 1)."""
    with pytest.raises(ValueError, match=r"positive|invalid.*'id'|'id'.*positive"):
        Todo.from_dict({"id": 0, "text": "test task"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "test task"})
    assert todo.id == 1

    # Also test a larger positive id
    todo2 = Todo.from_dict({"id": 42, "text": "another task"})
    assert todo2.id == 42
