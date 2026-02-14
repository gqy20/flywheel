"""Tests for Todo.id non-negative validation (Issue #3128).

These tests verify that:
1. Todo.from_dict rejects negative id values
2. Todo.from_dict accepts id = 0 as valid
3. Todo.from_dict accepts positive id values
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match=r"negative|non-negative|>= 0"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept id = 0 as valid."""
    todo = Todo.from_dict({"id": 0, "text": "task"})
    assert todo.id == 0
    assert todo.text == "task"


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1
    assert todo.text == "task"
