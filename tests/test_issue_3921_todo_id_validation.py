"""Tests for Todo.id non-negative integer validation (Issue #3921).

These tests verify that:
1. Todo.from_dict rejects negative id values
2. Todo.from_dict accepts zero and positive id values
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_negative_id() -> None:
    """Bug #3921: Todo.from_dict should reject negative id values."""
    with pytest.raises(ValueError, match="non-negative"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_from_dict_rejects_large_negative_id() -> None:
    """Bug #3921: Todo.from_dict should reject large negative id values."""
    with pytest.raises(ValueError, match="non-negative"):
        Todo.from_dict({"id": -999999, "text": "test"})


def test_todo_from_dict_accepts_zero_id() -> None:
    """Bug #3921: Todo.from_dict should accept id=0 (0 is non-negative)."""
    todo = Todo.from_dict({"id": 0, "text": "test"})
    assert todo.id == 0
    assert todo.text == "test"


def test_todo_from_dict_accepts_positive_id() -> None:
    """Bug #3921: Todo.from_dict should accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
    assert todo.text == "test"


def test_todo_from_dict_accepts_large_positive_id() -> None:
    """Bug #3921: Todo.from_dict should accept large positive id values."""
    todo = Todo.from_dict({"id": 999999, "text": "test"})
    assert todo.id == 999999
    assert todo.text == "test"
