"""Tests for Todo id validation (Issue #4510).

These tests verify that:
1. Todo id must be a positive integer (> 0)
2. Todo(id=0, text="...") raises ValueError
3. Todo(id=-1, text="...") raises ValueError
4. Todo(id=1, text="...") still works correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_id_zero_raises_value_error() -> None:
    """Todo with id=0 should raise ValueError."""
    with pytest.raises(ValueError, match="positive integer"):
        Todo(id=0, text="test")


def test_todo_id_negative_raises_value_error() -> None:
    """Todo with negative id should raise ValueError."""
    with pytest.raises(ValueError, match="positive integer"):
        Todo(id=-1, text="test")


def test_todo_id_negative_five_raises_value_error() -> None:
    """Todo with id=-5 should raise ValueError."""
    with pytest.raises(ValueError, match="positive integer"):
        Todo(id=-5, text="test")


def test_todo_id_positive_one_succeeds() -> None:
    """Todo with id=1 should work correctly."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1
    assert todo.text == "test"


def test_todo_id_positive_large_succeeds() -> None:
    """Todo with large positive id should work correctly."""
    todo = Todo(id=999, text="test")
    assert todo.id == 999


def test_from_dict_with_zero_id_raises_value_error() -> None:
    """Todo.from_dict with id=0 should raise ValueError."""
    with pytest.raises(ValueError, match="positive integer"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_from_dict_with_negative_id_raises_value_error() -> None:
    """Todo.from_dict with negative id should raise ValueError."""
    with pytest.raises(ValueError, match="positive integer"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_from_dict_with_positive_id_succeeds() -> None:
    """Todo.from_dict with positive id should work correctly."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
