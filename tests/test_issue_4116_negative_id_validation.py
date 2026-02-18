"""Regression tests for issue #4116: Todo.from_dict should reject negative id values."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_negative_id() -> None:
    """Bug #4116: Todo.from_dict() should reject negative id values."""
    with pytest.raises(ValueError, match=r"id.*must be a non-negative integer"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_from_dict_rejects_negative_large_id() -> None:
    """Bug #4116: Todo.from_dict() should reject any negative id, even large ones."""
    with pytest.raises(ValueError, match=r"id.*must be a non-negative integer"):
        Todo.from_dict({"id": -999999, "text": "test"})


def test_from_dict_accepts_zero_id() -> None:
    """Bug #4116: Todo.from_dict() should accept id=0 (edge case, non-negative)."""
    todo = Todo.from_dict({"id": 0, "text": "test"})
    assert todo.id == 0
    assert todo.text == "test"


def test_from_dict_accepts_positive_id() -> None:
    """Bug #4116: Todo.from_dict() should still accept positive id values."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
    assert todo.text == "test"


def test_direct_instantiation_rejects_negative_id() -> None:
    """Bug #4116: Direct Todo() instantiation should reject negative id values."""
    with pytest.raises(ValueError, match=r"id.*must be a non-negative integer"):
        Todo(id=-1, text="test")


def test_direct_instantiation_rejects_negative_large_id() -> None:
    """Bug #4116: Direct Todo() instantiation should reject any negative id."""
    with pytest.raises(ValueError, match=r"id.*must be a non-negative integer"):
        Todo(id=-999999, text="test")


def test_direct_instantiation_accepts_zero_id() -> None:
    """Bug #4116: Direct Todo() instantiation should accept id=0 (edge case)."""
    todo = Todo(id=0, text="test")
    assert todo.id == 0


def test_direct_instantiation_accepts_positive_id() -> None:
    """Bug #4116: Direct Todo() instantiation should accept positive id values."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1
