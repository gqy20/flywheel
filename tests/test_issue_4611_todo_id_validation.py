"""Tests for Todo id validation (Issue #4611).

These tests verify that:
1. Todo id must be a positive integer (>= 1)
2. Todo(id=0, ...) raises ValueError
3. Todo(id=-1, ...) raises ValueError
4. Todo.from_dict rejects id=0 and id=-1
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_id_must_be_positive_zero() -> None:
    """Bug #4611: Todo(id=0, ...) should raise ValueError."""
    with pytest.raises(ValueError, match="id must be a positive integer"):
        Todo(id=0, text="test")


def test_todo_id_must_be_positive_negative() -> None:
    """Bug #4611: Todo(id=-1, ...) should raise ValueError."""
    with pytest.raises(ValueError, match="id must be a positive integer"):
        Todo(id=-1, text="test")


def test_todo_id_accepts_one() -> None:
    """Bug #4611: Todo(id=1, ...) should be valid."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1


def test_todo_id_accepts_positive_integers() -> None:
    """Bug #4611: Todo should accept any positive integer."""
    todo = Todo(id=42, text="test")
    assert todo.id == 42


def test_from_dict_rejects_zero_id() -> None:
    """Bug #4611: Todo.from_dict should reject id=0."""
    with pytest.raises(ValueError, match="id must be a positive integer"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_from_dict_rejects_negative_id() -> None:
    """Bug #4611: Todo.from_dict should reject id=-1."""
    with pytest.raises(ValueError, match="id must be a positive integer"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_from_dict_accepts_positive_id() -> None:
    """Bug #4611: Todo.from_dict should accept id=1."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
