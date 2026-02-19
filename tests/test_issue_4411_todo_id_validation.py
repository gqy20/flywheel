"""Tests for Todo ID validation (Issue #4411).

These tests verify that:
1. Todo constructor rejects id=0
2. Todo constructor rejects negative IDs
3. Todo.from_dict rejects id=0
4. Todo.from_dict rejects negative IDs
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_id_zero() -> None:
    """Todo constructor should reject id=0."""
    with pytest.raises(ValueError, match=r"id.*must be.*positive|invalid.*id"):
        Todo(id=0, text="task")


def test_todo_constructor_rejects_negative_id() -> None:
    """Todo constructor should reject negative IDs."""
    with pytest.raises(ValueError, match=r"id.*must be.*positive|invalid.*id"):
        Todo(id=-1, text="task")


def test_todo_from_dict_rejects_id_zero() -> None:
    """Todo.from_dict should reject id=0."""
    with pytest.raises(ValueError, match=r"id.*must be.*positive|invalid.*id"):
        Todo.from_dict({"id": 0, "text": "task"})


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative IDs."""
    with pytest.raises(ValueError, match=r"id.*must be.*positive|invalid.*id"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_accepts_positive_id() -> None:
    """Todo constructor should accept positive IDs."""
    todo = Todo(id=1, text="task")
    assert todo.id == 1


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive IDs."""
    todo = Todo.from_dict({"id": 42, "text": "task"})
    assert todo.id == 42
