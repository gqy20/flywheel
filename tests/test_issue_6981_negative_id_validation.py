"""Tests for negative id validation in Todo.from_dict (Issue #6981).

These tests verify that:
1. Todo.from_dict rejects negative integer id values
2. Todo.from_dict rejects negative string id values
3. Todo.from_dict still accepts id=0 (zero is valid)
4. Todo.from_dict still accepts positive id values
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_int_id() -> None:
    """Todo.from_dict should reject negative integer id values."""
    with pytest.raises(ValueError, match=r"non-negative"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_rejects_negative_string_id() -> None:
    """Todo.from_dict should reject negative string id values."""
    with pytest.raises(ValueError, match=r"non-negative"):
        Todo.from_dict({"id": "-5", "text": "task"})


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept id=0 (zero is valid)."""
    todo = Todo.from_dict({"id": 0, "text": "task"})
    assert todo.id == 0


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1
