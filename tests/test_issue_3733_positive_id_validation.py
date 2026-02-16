"""Tests for positive integer id validation (Issue #3733).

These tests verify that Todo.from_dict validates that 'id' must be a positive integer (> 0).
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative values for 'id' field."""
    with pytest.raises(ValueError, match=r"positive"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject zero value for 'id' field."""
    with pytest.raises(ValueError, match=r"positive"):
        Todo.from_dict({"id": 0, "text": "task"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive values for 'id' field."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1

    todo_large = Todo.from_dict({"id": 9999, "text": "task"})
    assert todo_large.id == 9999
