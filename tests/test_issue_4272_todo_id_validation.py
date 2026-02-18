"""Regression tests for Issue #4272: No validation for negative or zero id values.

These tests verify that:
1. Todo constructor with id=0 raises ValueError
2. Todo constructor with negative id raises ValueError
3. Todo.from_dict with id=0 raises ValueError
4. Todo.from_dict with negative id raises ValueError
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_zero_id() -> None:
    """Todo constructor should reject id=0."""
    with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
        Todo(id=0, text="test")


def test_todo_constructor_rejects_negative_id() -> None:
    """Todo constructor should reject negative id values."""
    with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
        Todo(id=-1, text="test")


def test_todo_constructor_rejects_large_negative_id() -> None:
    """Todo constructor should reject large negative id values."""
    with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
        Todo(id=-100, text="test")


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0."""
    with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
        Todo.from_dict({"id": -5, "text": "test"})


def test_todo_from_dict_rejects_large_negative_id() -> None:
    """Todo.from_dict should reject large negative id values."""
    with pytest.raises(ValueError, match=r"id.*positive|positive.*id"):
        Todo.from_dict({"id": -100, "text": "test"})


def test_todo_accepts_positive_id() -> None:
    """Todo constructor should accept positive id values."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 42, "text": "test"})
    assert todo.id == 42
