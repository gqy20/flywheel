"""Tests for Todo id validation (Issue #5446).

These tests verify that:
1. Todo constructor validates id is a positive integer (id >= 1)
2. Negative ids raise ValueError
3. Zero id raises ValueError
4. Positive ids work correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_rejects_negative_id() -> None:
    """Todo(id=-1, ...) should raise ValueError."""
    with pytest.raises(ValueError, match=r"id.*positive"):
        Todo(id=-1, text="test")


def test_todo_rejects_zero_id() -> None:
    """Todo(id=0, ...) should raise ValueError."""
    with pytest.raises(ValueError, match=r"id.*positive"):
        Todo(id=0, text="test")


def test_todo_accepts_positive_id() -> None:
    """Todo(id=1, ...) should create successfully."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1


def test_todo_accepts_large_positive_id() -> None:
    """Todo should accept large positive ids."""
    todo = Todo(id=999999, text="test")
    assert todo.id == 999999


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id."""
    with pytest.raises(ValueError, match=r"id.*positive"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject zero id."""
    with pytest.raises(ValueError, match=r"id.*positive"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
