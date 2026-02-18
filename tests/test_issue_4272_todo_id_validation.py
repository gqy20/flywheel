"""Tests for Todo id validation (Issue #4272).

These tests verify that:
1. Todo constructor rejects id=0 with ValueError
2. Todo constructor rejects negative id with ValueError
3. Todo.from_dict rejects id=0 with ValueError
4. Todo.from_dict rejects negative id with ValueError
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_zero_id() -> None:
    """Todo constructor should reject id=0 with clear error message."""
    with pytest.raises(ValueError, match=r"id.*positive|positive.*integer"):
        Todo(id=0, text="test")


def test_todo_constructor_rejects_negative_id() -> None:
    """Todo constructor should reject negative id with clear error message."""
    with pytest.raises(ValueError, match=r"id.*positive|positive.*integer"):
        Todo(id=-1, text="test")


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0 with clear error message."""
    with pytest.raises(ValueError, match=r"id.*positive|positive.*integer"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id with clear error message."""
    with pytest.raises(ValueError, match=r"id.*positive|positive.*integer"):
        Todo.from_dict({"id": -5, "text": "test"})


def test_todo_constructor_accepts_positive_id() -> None:
    """Todo constructor should accept positive id values."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 42, "text": "test"})
    assert todo.id == 42
