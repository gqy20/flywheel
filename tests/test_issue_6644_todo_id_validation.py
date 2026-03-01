"""Tests for Todo.id validation (Issue #6644).

These tests verify that Todo.from_dict rejects non-positive IDs
(negative and zero values) with clear error messages.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0 with clear error message."""
    with pytest.raises(ValueError, match=r"positive"):
        Todo.from_dict({"id": 0, "text": "task"})


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values with clear error message."""
    with pytest.raises(ValueError, match=r"positive"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values (id >= 1)."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1
    assert todo.text == "task"
