"""Tests for negative id validation (Issue #6925).

These tests verify that:
1. Negative id values are rejected with a clear error message
2. Zero (0) is accepted as a valid id
3. Positive id values continue to work
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match=r"'id'.*non-negative|'id'.*negative"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept zero (0) as a valid id."""
    todo = Todo.from_dict({"id": 0, "text": "task"})
    assert todo.id == 0
    assert todo.text == "task"


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1
    assert todo.text == "task"
