"""Tests for Todo.from_dict negative id validation (Issue #3819).

These tests verify that:
1. Todo.from_dict rejects negative id values with ValueError
2. Todo.from_dict accepts id=0 (design decision: valid but unusual)
3. Todo.from_dict continues to accept positive id values
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_negative_id() -> None:
    """Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": -1, "text": "test"})
    assert "id" in str(exc_info.value).lower()
    assert "negative" in str(exc_info.value).lower() or "-1" in str(exc_info.value)


def test_from_dict_rejects_negative_id_string() -> None:
    """Todo.from_dict should reject negative id values passed as strings."""
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": "-42", "text": "test"})
    assert "id" in str(exc_info.value).lower()


def test_from_dict_accepts_zero_id() -> None:
    """Todo.from_dict should accept id=0 (edge case but valid)."""
    todo = Todo.from_dict({"id": 0, "text": "test"})
    assert todo.id == 0


def test_from_dict_accepts_positive_id() -> None:
    """Todo.from_dict should accept positive id values normally."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1

    todo2 = Todo.from_dict({"id": 999, "text": "another test"})
    assert todo2.id == 999


def test_from_dict_accepts_large_positive_id() -> None:
    """Todo.from_dict should accept large positive id values."""
    todo = Todo.from_dict({"id": 1000000, "text": "test"})
    assert todo.id == 1000000
