"""Tests for negative id validation (Issue #6925).

These tests verify that:
1. Negative id values are rejected with clear error messages
2. Zero is accepted as a valid id (0 is non-negative)
3. Positive ids continue to work correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match=r"'id'.*non-negative|'id'.*must be.*>= ?0"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept id=0 (zero is non-negative)."""
    todo = Todo.from_dict({"id": 0, "text": "task"})
    assert todo.id == 0
    assert todo.text == "task"


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should continue to accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1
    assert todo.text == "task"
