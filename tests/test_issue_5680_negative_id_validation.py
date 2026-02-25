"""Tests for negative/zero ID validation (Issue #5680).

These tests verify that:
1. Todo.from_dict rejects negative IDs
2. Todo.from_dict rejects zero ID
3. Todo.from_dict still accepts positive IDs
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative 'id' values."""
    with pytest.raises(ValueError, match=r"'id'.*positive|'id'.*>= ?1|'id'.*greater"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject zero as 'id' value."""
    with pytest.raises(ValueError, match=r"'id'.*positive|'id'.*>= ?1|'id'.*greater"):
        Todo.from_dict({"id": 0, "text": "task"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive 'id' values."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1


def test_todo_from_dict_accepts_large_positive_id() -> None:
    """Todo.from_dict should accept large positive 'id' values."""
    todo = Todo.from_dict({"id": 1000000, "text": "task"})
    assert todo.id == 1000000
