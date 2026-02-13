"""Tests for positive id validation (Issue #3118).

These tests verify that:
1. Todo constructor rejects zero and negative ids
2. Todo.from_dict rejects zero and negative ids
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_zero_id() -> None:
    """Todo constructor should reject zero as id."""
    with pytest.raises(ValueError, match=r"id.*must be.*positive|positive.*id"):
        Todo(id=0, text="test task")


def test_todo_constructor_rejects_negative_id() -> None:
    """Todo constructor should reject negative id values."""
    with pytest.raises(ValueError, match=r"id.*must be.*positive|positive.*id"):
        Todo(id=-1, text="test task")


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject zero as id."""
    with pytest.raises(ValueError, match=r"id.*must be.*positive|positive.*id"):
        Todo.from_dict({"id": 0, "text": "test task"})


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match=r"id.*must be.*positive|positive.*id"):
        Todo.from_dict({"id": -5, "text": "test task"})


def test_todo_constructor_accepts_positive_id() -> None:
    """Todo constructor should accept positive id values."""
    todo = Todo(id=1, text="test task")
    assert todo.id == 1


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 42, "text": "test task"})
    assert todo.id == 42
