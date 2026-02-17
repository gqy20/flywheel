"""Tests for negative id validation (Issue #4046).

These tests verify that:
1. Todo.from_dict rejects negative integers for 'id' field
2. Todo.from_dict accepts zero as a valid 'id' (id=0 is valid)
3. Todo.from_dict continues to accept positive integers for 'id'
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative integers for 'id' field."""
    with pytest.raises(ValueError, match=r"negative|non-negative"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept id=0 as a valid id."""
    todo = Todo.from_dict({"id": 0, "text": "task"})
    assert todo.id == 0
    assert todo.text == "task"


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should continue to accept positive integers for 'id'."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1
    assert todo.text == "task"
