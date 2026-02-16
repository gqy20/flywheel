"""Tests for Todo positive ID validation (Issue #3707).

These tests verify that:
1. Todo(id=0, text='test') raises ValueError with message about positive ID
2. Todo(id=-1, text='test') raises ValueError with message about positive ID
3. Todo.from_dict({'id': -1, 'text': 'test'}) raises ValueError
4. Valid positive IDs continue to work
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_rejects_zero_id() -> None:
    """Todo should reject id=0 as invalid (IDs must be positive)."""
    with pytest.raises(ValueError, match=r"positive|greater than 0|id must be"):
        Todo(id=0, text="test task")


def test_todo_rejects_negative_id() -> None:
    """Todo should reject negative id values."""
    with pytest.raises(ValueError, match=r"positive|greater than 0|id must be"):
        Todo(id=-1, text="test task")


def test_todo_rejects_large_negative_id() -> None:
    """Todo should reject large negative id values."""
    with pytest.raises(ValueError, match=r"positive|greater than 0|id must be"):
        Todo(id=-999, text="test task")


def test_todo_accepts_positive_id() -> None:
    """Todo should accept valid positive id values."""
    todo = Todo(id=1, text="valid task")
    assert todo.id == 1
    assert todo.text == "valid task"


def test_todo_accepts_large_positive_id() -> None:
    """Todo should accept large positive id values."""
    todo = Todo(id=999999, text="valid task")
    assert todo.id == 999999


def test_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0 as invalid."""
    with pytest.raises(ValueError, match=r"positive|greater than 0|id must be"):
        Todo.from_dict({"id": 0, "text": "test task"})


def test_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match=r"positive|greater than 0|id must be"):
        Todo.from_dict({"id": -1, "text": "test task"})


def test_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept valid positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "valid task"})
    assert todo.id == 1
    assert todo.text == "valid task"
