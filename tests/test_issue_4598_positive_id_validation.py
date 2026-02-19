"""Tests for issue #4598: Todo.from_dict should reject negative and zero IDs."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_negative_id() -> None:
    """Bug #4598: Todo.from_dict() should reject negative IDs."""
    with pytest.raises(ValueError, match="'id' must be a positive integer"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_from_dict_rejects_zero_id() -> None:
    """Bug #4598: Todo.from_dict() should reject zero ID."""
    with pytest.raises(ValueError, match="'id' must be a positive integer"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_from_dict_accepts_positive_id() -> None:
    """Bug #4598: Todo.from_dict() should accept positive IDs."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
    assert todo.text == "test"
