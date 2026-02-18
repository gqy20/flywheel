"""Tests for Todo id non-negative validation (Issue #4116).

These tests verify that:
1. Negative id values are rejected with clear error messages
2. Zero id values are rejected with clear error messages
3. Positive id values are accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative integers for 'id' field."""
    with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*positive|'id'.*non-negative|'id'.*must be"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject zero for 'id' field."""
    with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*positive|'id'.*must be"):
        Todo.from_dict({"id": 0, "text": "task"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive integers for 'id' field."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1

    todo2 = Todo.from_dict({"id": 100, "text": "task2"})
    assert todo2.id == 100
