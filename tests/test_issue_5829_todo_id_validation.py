"""Tests for Todo id validation (Issue #5829).

These tests verify that:
1. Todo(id=0, ...) raises ValueError
2. Todo(id=-1, ...) raises ValueError
3. Todo.from_dict with negative/zero id raises ValueError
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_rejects_zero_id() -> None:
    """Todo should reject id=0 as invalid."""
    with pytest.raises(ValueError, match=r"id.*positive|id.*greater.*0|invalid.*id"):
        Todo(id=0, text="test")


def test_todo_rejects_negative_id() -> None:
    """Todo should reject negative id values."""
    with pytest.raises(ValueError, match=r"id.*positive|id.*greater.*0|invalid.*id"):
        Todo(id=-1, text="test")


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0 as invalid."""
    with pytest.raises(ValueError, match=r"id.*positive|id.*greater.*0|invalid.*id"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match=r"id.*positive|id.*greater.*0|invalid.*id"):
        Todo.from_dict({"id": -5, "text": "test"})


def test_todo_accepts_positive_id() -> None:
    """Todo should accept positive id values."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 42, "text": "test"})
    assert todo.id == 42
