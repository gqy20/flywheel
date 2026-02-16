"""Tests for negative ID validation (Issue #3805).

These tests verify that:
1. Todo constructor rejects negative ID values
2. Todo.from_dict rejects negative ID values
3. Positive and zero IDs are still accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_negative_id() -> None:
    """Todo constructor should reject negative ID values."""
    with pytest.raises(ValueError, match=r"negative|'id'.*invalid|'id'.*must"):
        Todo(id=-1, text="test")


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative ID values."""
    with pytest.raises(ValueError, match=r"negative|'id'.*invalid|'id'.*must"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_constructor_accepts_zero_id() -> None:
    """Todo constructor should accept zero as a valid ID."""
    todo = Todo(id=0, text="test")
    assert todo.id == 0


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept zero as a valid ID."""
    todo = Todo.from_dict({"id": 0, "text": "test"})
    assert todo.id == 0


def test_todo_constructor_accepts_positive_id() -> None:
    """Todo constructor should accept positive ID values."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive ID values."""
    todo = Todo.from_dict({"id": 42, "text": "test"})
    assert todo.id == 42
