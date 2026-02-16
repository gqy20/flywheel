"""Tests for negative ID validation (Issue #3805).

These tests verify that:
1. Todo(id=-1, ...) raises ValueError when created directly
2. Todo.from_dict({'id': -1, ...}) raises ValueError
3. Positive and zero IDs are still accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_direct_construction_rejects_negative_id() -> None:
    """Todo construction should reject negative ID values."""
    with pytest.raises(ValueError, match=r"negative|'id'.*non-negative|id.*>= ?0"):
        Todo(id=-1, text="test")


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative ID values."""
    with pytest.raises(ValueError, match=r"negative|'id'.*non-negative|id.*>= ?0"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_direct_construction_accepts_zero_id() -> None:
    """Todo construction should accept zero ID value."""
    # Zero should be accepted (per issue acceptance criteria)
    todo = Todo(id=0, text="test")
    assert todo.id == 0


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept zero ID value."""
    todo = Todo.from_dict({"id": 0, "text": "test"})
    assert todo.id == 0


def test_todo_direct_construction_accepts_positive_id() -> None:
    """Todo construction should accept positive ID values."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive ID values."""
    todo = Todo.from_dict({"id": 42, "text": "test"})
    assert todo.id == 42
