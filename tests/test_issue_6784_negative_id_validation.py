"""Tests for issue #6784: Todo.from_dict rejects negative id values."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_negative_id() -> None:
    """Bug #6784: Todo.from_dict() should reject negative id values."""
    with pytest.raises(ValueError, match=r"'id'.*non-negative"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_from_dict_accepts_zero_id() -> None:
    """Bug #6784: Todo.from_dict() should accept id=0 (valid non-negative)."""
    todo = Todo.from_dict({"id": 0, "text": "test"})
    assert todo.id == 0
    assert todo.text == "test"


def test_from_dict_accepts_positive_id() -> None:
    """Bug #6784: Todo.from_dict() should continue to work with positive ids."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
    assert todo.text == "test"
