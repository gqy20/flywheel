"""Tests for negative ID validation in Todo.from_dict (Issue #3908).

These tests verify that:
1. Todo.from_dict rejects negative IDs with clear error message
2. Todo.from_dict accepts ID=0 (non-negative) as valid
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative IDs with clear error message."""
    with pytest.raises(ValueError, match=r"'id'.*non-negative|non-negative.*'id'"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept ID=0 as valid (non-negative)."""
    todo = Todo.from_dict({"id": 0, "text": "test"})
    assert todo.id == 0


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive IDs as valid."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
