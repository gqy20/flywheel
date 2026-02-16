"""Tests for Todo id validation (Issue #3847).

These tests verify that:
1. Todo.__init__ rejects id <= 0
2. Todo.from_dict rejects id <= 0
3. Valid positive ids continue to work
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


# Tests for Todo.__init__ validation
def test_todo_init_rejects_zero_id() -> None:
    """Todo.__init__ should reject id=0."""
    with pytest.raises(ValueError, match=r"id.*positive|id.*greater than 0"):
        Todo(id=0, text="test")


def test_todo_init_rejects_negative_id() -> None:
    """Todo.__init__ should reject negative id values."""
    with pytest.raises(ValueError, match=r"id.*positive|id.*greater than 0"):
        Todo(id=-1, text="test")


# Tests for Todo.from_dict validation
def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0."""
    with pytest.raises(ValueError, match=r"id.*positive|id.*greater than 0"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match=r"id.*positive|id.*greater than 0"):
        Todo.from_dict({"id": -5, "text": "test"})


# Positive tests (regression - ensure valid cases still work)
def test_todo_init_accepts_positive_id() -> None:
    """Todo.__init__ should accept id=1."""
    todo = Todo(id=1, text="valid")
    assert todo.id == 1


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept valid positive id."""
    todo = Todo.from_dict({"id": 10, "text": "valid"})
    assert todo.id == 10
