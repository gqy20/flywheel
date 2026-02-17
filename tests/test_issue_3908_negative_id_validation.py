"""Tests for Todo.from_dict negative ID validation (Issue #3908).

These tests verify that Todo.from_dict rejects negative IDs to ensure
consistency with the storage pattern where IDs are always positive.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative IDs."""
    with pytest.raises(ValueError, match=r"'id'.*non-negative|'id'.*positive"):
        Todo.from_dict({"id": -1, "text": "test task"})


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept zero as a valid ID (non-negative)."""
    # ID=0 is explicitly defined as acceptable (non-negative)
    todo = Todo.from_dict({"id": 0, "text": "test task"})
    assert todo.id == 0
    assert todo.text == "test task"


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive IDs."""
    todo = Todo.from_dict({"id": 42, "text": "test task"})
    assert todo.id == 42
    assert todo.text == "test task"
