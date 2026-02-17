"""Tests for negative ID validation (Issue #4046).

These tests verify that:
1. Todo.from_dict rejects negative integers for 'id' field
2. Todo.from_dict accepts zero as a valid 'id' value
3. Todo.from_dict accepts positive integers as valid 'id' values
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative integers for 'id' field."""
    with pytest.raises(ValueError, match=r"'id'.*non-negative|'id'.*negative|negative"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_rejects_large_negative_id() -> None:
    """Todo.from_dict should reject large negative integers for 'id' field."""
    with pytest.raises(ValueError, match=r"'id'.*non-negative|'id'.*negative|negative"):
        Todo.from_dict({"id": -999, "text": "task"})


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept zero as a valid 'id' value."""
    todo = Todo.from_dict({"id": 0, "text": "task"})
    assert todo.id == 0


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive integers for 'id' field."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1
