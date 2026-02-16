"""Tests for positive ID validation in Todo.from_dict() (Issue #3789).

These tests verify that:
1. Todo.from_dict rejects id=0 with a clear error message
2. Todo.from_dict rejects negative IDs with a clear error message
3. Todo.from_dict accepts positive IDs (id=1+)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should reject id=0 as invalid."""
    with pytest.raises(ValueError, match=r"positive integer"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative IDs as invalid."""
    with pytest.raises(ValueError, match=r"positive integer"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive IDs (id >= 1)."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
    assert todo.text == "test"
