"""Tests for positive ID validation in Todo.from_dict (Issue #3789).

These tests verify that:
1. Todo.from_dict rejects id=0 with clear error message
2. Todo.from_dict rejects negative id values with clear error message
3. Todo.from_dict accepts positive id values (id >= 1)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0 with clear error about positive integer."""
    with pytest.raises(ValueError, match=r"positive.*integer|'id'.*positive"):
        Todo.from_dict({"id": 0, "text": "task"})


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values with clear error message."""
    with pytest.raises(ValueError, match=r"positive.*integer|'id'.*positive"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values (id >= 1)."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1
    assert todo.text == "task"
