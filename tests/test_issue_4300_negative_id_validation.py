"""Tests for negative ID validation in from_dict() (Issue #4300).

These tests verify that:
1. Negative IDs are rejected with clear error message
2. Zero (0) is accepted as a valid ID
3. Positive IDs continue to work
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative IDs with clear error message."""
    with pytest.raises(ValueError, match=r"'id'.*non-negative|non-negative.*'id'"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept zero as a valid ID."""
    todo = Todo.from_dict({"id": 0, "text": "task"})
    assert todo.id == 0


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should continue to accept positive IDs."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1
