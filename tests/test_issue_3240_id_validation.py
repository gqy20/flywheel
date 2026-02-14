"""Tests for ID validation in Todo.from_dict (Issue #3240).

These tests verify that Todo.from_dict rejects invalid 'id' values:
1. id=0 should raise ValueError
2. negative id should raise ValueError
3. positive id should work as before
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0 as invalid."""
    with pytest.raises(ValueError, match=r"'id'.*positive|invalid.*'id'"):
        Todo.from_dict({"id": 0, "text": "task"})


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match=r"'id'.*positive|invalid.*'id'"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept valid positive id values (existing behavior)."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1
    assert todo.text == "task"
