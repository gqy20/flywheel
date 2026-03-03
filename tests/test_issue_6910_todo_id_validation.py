"""Tests for Todo ID validation (Issue #6910).

These tests verify that:
1. Todo rejects zero or negative IDs with clear error messages
2. Todo.from_dict rejects zero or negative IDs with clear error messages
3. Positive IDs work as expected
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_rejects_zero_id() -> None:
    """Todo should reject id=0 with clear error message."""
    with pytest.raises(ValueError, match=r"id.*positive|positive.*integer"):
        Todo(id=0, text="test")


def test_todo_rejects_negative_id() -> None:
    """Todo should reject negative id with clear error message."""
    with pytest.raises(ValueError, match=r"id.*positive|positive.*integer"):
        Todo(id=-1, text="test")


def test_todo_accepts_positive_id() -> None:
    """Todo should accept positive id values."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1
    assert todo.text == "test"


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0 with clear error message."""
    with pytest.raises(ValueError, match=r"id.*positive|positive.*integer"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id with clear error message."""
    with pytest.raises(ValueError, match=r"id.*positive|positive.*integer"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
    assert todo.text == "test"
