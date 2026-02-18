"""Tests for Todo.id positive integer validation (Issue #4284).

These tests verify that:
1. Todo.from_dict rejects negative integers for 'id' field
2. Todo.from_dict rejects zero for 'id' field
3. Todo.from_dict continues to accept positive integers for 'id' field
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative integers for 'id' field."""
    with pytest.raises(ValueError, match=r"id must be a positive integer|positive.*id"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject zero for 'id' field (ids start at 1)."""
    with pytest.raises(ValueError, match=r"id must be a positive integer|positive.*id"):
        Todo.from_dict({"id": 0, "text": "task"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive integers for 'id' field."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1

    todo2 = Todo.from_dict({"id": 42, "text": "another task"})
    assert todo2.id == 42
