"""Tests for negative ID validation (Issue #6106).

These tests verify that:
1. Todo.from_dict rejects negative IDs with a clear error message
2. Todo.from_dict accepts zero as a valid ID
3. Todo.from_dict accepts positive IDs
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative IDs."""
    with pytest.raises(ValueError, match=r"non-negative|'id'.*must be"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept zero as a valid ID."""
    todo = Todo.from_dict({"id": 0, "text": "test"})
    assert todo.id == 0


def test_todo_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive IDs."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
