"""Tests for ID validation in Todo.from_dict (Issue #6337).

These tests verify that:
1. Todo.from_dict rejects negative ID values
2. Todo.from_dict rejects zero ID value
3. Todo.from_dict accepts positive ID values
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative ID values."""
    with pytest.raises(ValueError, match=r"'id'.*positive|'id'.*must be"):
        Todo.from_dict({"id": -1, "text": "task"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject zero ID value."""
    with pytest.raises(ValueError, match=r"'id'.*positive|'id'.*must be"):
        Todo.from_dict({"id": 0, "text": "task"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive ID values."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.id == 1
    assert todo.text == "task"

    todo2 = Todo.from_dict({"id": 100, "text": "another task"})
    assert todo2.id == 100
