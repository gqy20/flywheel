"""Tests for negative ID validation (Issue #4327).

These tests verify that:
1. Todo.from_dict rejects negative IDs with clear error message
2. Todo.from_dict rejects zero ID with clear error message
3. Todo.from_dict still accepts positive IDs
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative IDs with clear error message."""
    with pytest.raises(ValueError, match=r"id must be positive|'id'.*positive"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject zero ID with clear error message."""
    with pytest.raises(ValueError, match=r"id must be positive|'id'.*positive"):
        Todo.from_dict({"id": 0, "text": "task"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive IDs."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1

    todo2 = Todo.from_dict({"id": 42, "text": "another task"})
    assert todo2.id == 42
