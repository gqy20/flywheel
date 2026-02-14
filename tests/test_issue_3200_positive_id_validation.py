"""Tests for positive id validation in Todo.from_dict (Issue #3200).

These tests verify that:
1. Todo.from_dict rejects negative id values
2. Todo.from_dict rejects zero as an id value
3. Todo.from_dict accepts positive id values
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match=r"positive integer|'id'.*positive"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject zero as an id value."""
    with pytest.raises(ValueError, match=r"positive integer|'id'.*positive"):
        Todo.from_dict({"id": 0, "text": "task"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1
    assert todo.text == "task"


def test_todo_from_dict_accepts_large_positive_id() -> None:
    """Todo.from_dict should accept large positive id values."""
    todo = Todo.from_dict({"id": 999999, "text": "task"})
    assert todo.id == 999999
