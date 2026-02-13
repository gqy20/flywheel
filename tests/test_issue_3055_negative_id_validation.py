"""Tests for negative ID validation (Issue #3055).

These tests verify that:
1. Todo.from_dict rejects negative ID values
2. Todo.from_dict rejects zero ID values
3. Todo.from_dict accepts positive ID values
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative 'id' values."""
    with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*positive|'id'.*greater"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject zero 'id' values (semantically invalid)."""
    with pytest.raises(ValueError, match=r"invalid.*'id'|'id'.*positive|'id'.*greater"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive 'id' values."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
    assert todo.text == "test"

    todo2 = Todo.from_dict({"id": 100, "text": "another test"})
    assert todo2.id == 100
