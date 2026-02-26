"""Tests for Todo ID validation (Issue #5829).

These tests verify that:
1. Todo rejects negative IDs with ValueError
2. Todo rejects zero ID with ValueError
3. Todo.from_dict rejects negative IDs with ValueError
4. Todo.from_dict rejects zero ID with ValueError
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_rejects_negative_id() -> None:
    """Todo should reject negative IDs."""
    with pytest.raises(ValueError, match=r"id.*positive|'id'.*greater|invalid.*id"):
        Todo(id=-1, text="test")


def test_todo_rejects_zero_id() -> None:
    """Todo should reject zero ID."""
    with pytest.raises(ValueError, match=r"id.*positive|'id'.*greater|invalid.*id"):
        Todo(id=0, text="test")


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative IDs with clear error message."""
    with pytest.raises(ValueError, match=r"id.*positive|'id'.*greater|invalid.*id"):
        Todo.from_dict({"id": -5, "text": "test"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject zero ID with clear error message."""
    with pytest.raises(ValueError, match=r"id.*positive|'id'.*greater|invalid.*id"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_todo_accepts_positive_id() -> None:
    """Todo should accept positive IDs."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1
    assert todo.text == "test"


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive IDs."""
    todo = Todo.from_dict({"id": 42, "text": "test"})
    assert todo.id == 42
    assert todo.text == "test"
