"""Tests for Todo.from_dict positive id validation (Issue #3200).

These tests verify that:
1. Todo.from_dict rejects negative id values with ValueError
2. Todo.from_dict rejects zero id value with ValueError
3. Todo.from_dict accepts positive id values
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should raise ValueError for negative id values."""
    with pytest.raises(ValueError, match="'id' must be a positive integer"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_from_dict_rejects_zero_id() -> None:
    """Todo.from_dict should raise ValueError for zero id value."""
    with pytest.raises(ValueError, match="'id' must be a positive integer"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
    assert todo.text == "test"


def test_from_dict_accepts_larger_positive_id() -> None:
    """Todo.from_dict should accept larger positive id values."""
    todo = Todo.from_dict({"id": 999999, "text": "test"})
    assert todo.id == 999999
