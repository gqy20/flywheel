"""Tests for Todo id validation (Issue #3692).

These tests verify that:
1. Todo.__init__ rejects id=0 with ValueError
2. Todo.__init__ rejects negative id with ValueError
3. Todo.__init__ accepts positive id values (id >= 1)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_zero_id() -> None:
    """Todo(id=0, ...) should raise ValueError."""
    with pytest.raises(ValueError, match="id must be a positive integer"):
        Todo(id=0, text="test")


def test_todo_init_rejects_negative_id() -> None:
    """Todo(id=-1, ...) should raise ValueError."""
    with pytest.raises(ValueError, match="id must be a positive integer"):
        Todo(id=-1, text="test")


def test_todo_init_rejects_various_negative_ids() -> None:
    """Todo should reject various negative id values."""
    for negative_id in [-100, -2, -999]:
        with pytest.raises(ValueError, match="id must be a positive integer"):
            Todo(id=negative_id, text="test")


def test_todo_init_accepts_positive_id() -> None:
    """Todo(id=1, text='test') should work normally."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1
    assert todo.text == "test"


def test_todo_init_accepts_large_positive_id() -> None:
    """Todo should accept large positive id values."""
    todo = Todo(id=999999, text="large id task")
    assert todo.id == 999999


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0."""
    with pytest.raises(ValueError, match="id must be a positive integer"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match="id must be a positive integer"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
