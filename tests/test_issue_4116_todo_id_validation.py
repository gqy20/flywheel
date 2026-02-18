"""Tests for Todo id validation (Issue #4116).

These tests verify that:
1. Todo.from_dict rejects negative id values
2. Todo.from_dict accepts id = 0 (boundary case)
3. Todo.from_dict accepts positive id values
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*non-negative|'id'.*positive"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_rejects_negative_id_large() -> None:
    """Todo.from_dict should reject large negative id values."""
    with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*non-negative|'id'.*positive"):
        Todo.from_dict({"id": -999, "text": "task"})


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept id = 0 (boundary case).

    Note: Based on the issue, id >= 0 is acceptable since next_id starts from 1
    and we want to allow 0 as a valid non-negative integer.
    """
    todo = Todo.from_dict({"id": 0, "text": "task with zero id"})
    assert todo.id == 0
    assert todo.text == "task with zero id"


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1
    assert todo.text == "task"


def test_todo_from_dict_accepts_large_positive_id() -> None:
    """Todo.from_dict should accept large positive id values."""
    todo = Todo.from_dict({"id": 999999, "text": "task"})
    assert todo.id == 999999
