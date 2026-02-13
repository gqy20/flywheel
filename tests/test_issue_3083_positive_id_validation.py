"""Tests for Todo.from_dict() id validation (Issue #3083).

These tests verify that:
1. Negative id values are rejected with clear error messages
2. Zero id values are rejected with clear error messages
3. Positive id values are accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match=r"positive integer"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject zero id value."""
    with pytest.raises(ValueError, match=r"positive integer"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
    assert todo.text == "test"
