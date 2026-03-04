"""Tests for Todo id validation (Issue #7106)."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_negative_id() -> None:
    """Bug #7106: Todo.__init__ should reject negative id values."""
    with pytest.raises(ValueError, match="'id' must be a non-negative integer"):
        Todo(id=-1, text="test")


def test_todo_init_accepts_zero_id() -> None:
    """Bug #7106: Todo.__init__ should accept id=0 as valid."""
    todo = Todo(id=0, text="test")
    assert todo.id == 0
    assert todo.text == "test"


def test_todo_init_accepts_positive_id() -> None:
    """Bug #7106: Todo.__init__ should accept positive id values."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1
    assert todo.text == "test"
