"""Tests for Todo id validation (Issue #4510).

These tests verify that:
1. Todo id field rejects zero
2. Todo id field rejects negative values
3. Todo id field accepts positive integers
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_id_zero_raises_value_error() -> None:
    """Todo(id=0, text="test") should raise ValueError with message about positive integer."""
    with pytest.raises(ValueError, match="positive integer"):
        Todo(id=0, text="test")


def test_todo_id_negative_raises_value_error() -> None:
    """Todo(id=-1, text="test") should raise ValueError with message about positive integer."""
    with pytest.raises(ValueError, match="positive integer"):
        Todo(id=-1, text="test")


def test_todo_id_negative_five_raises_value_error() -> None:
    """Todo(id=-5, text="test") should raise ValueError with message about positive integer."""
    with pytest.raises(ValueError, match="positive integer"):
        Todo(id=-5, text="test")


def test_todo_id_one_succeeds() -> None:
    """Todo(id=1, text="test") should work correctly."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1
    assert todo.text == "test"


def test_todo_id_large_positive_succeeds() -> None:
    """Todo should accept large positive integers."""
    todo = Todo(id=999999, text="test large id")
    assert todo.id == 999999


def test_todo_from_dict_id_zero_raises_value_error() -> None:
    """Todo.from_dict should reject id=0."""
    with pytest.raises(ValueError, match="positive integer"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_todo_from_dict_id_negative_raises_value_error() -> None:
    """Todo.from_dict should reject negative id."""
    with pytest.raises(ValueError, match="positive integer"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_from_dict_id_positive_succeeds() -> None:
    """Todo.from_dict should accept positive id."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
