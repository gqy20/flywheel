"""Tests for negative ID validation (Issue #6744).

These tests verify that:
1. Todo.from_dict rejects negative 'id' values
2. Todo.from_dict accepts id=0 (boundary case)
3. Todo.from_dict accepts positive id values as before
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative 'id' values."""
    with pytest.raises(ValueError, match=r"'id'.*non-negative|non-negative.*'id'"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_rejects_large_negative_id() -> None:
    """Todo.from_dict should reject large negative 'id' values."""
    with pytest.raises(ValueError, match=r"'id'.*non-negative|non-negative.*'id'"):
        Todo.from_dict({"id": -100, "text": "task"})


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept id=0 (boundary case)."""
    todo = Todo.from_dict({"id": 0, "text": "task"})
    assert todo.id == 0


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive 'id' values as before."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1

    todo2 = Todo.from_dict({"id": 999, "text": "another task"})
    assert todo2.id == 999
