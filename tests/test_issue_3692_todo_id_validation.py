"""Tests for Todo.__init__ id validation (Issue #3692).

These tests verify that:
1. Todo.__init__ rejects id=0
2. Todo.__init__ rejects negative id values
3. Todo.__init__ accepts positive id values
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_init_rejects_zero_id() -> None:
    """Todo.__init__ should reject id=0 with ValueError."""
    with pytest.raises(ValueError, match="id must be a positive integer"):
        Todo(id=0, text="test")


def test_todo_init_rejects_negative_id() -> None:
    """Todo.__init__ should reject negative id values with ValueError."""
    with pytest.raises(ValueError, match="id must be a positive integer"):
        Todo(id=-1, text="test")


def test_todo_init_rejects_large_negative_id() -> None:
    """Todo.__init__ should reject large negative id values with ValueError."""
    with pytest.raises(ValueError, match="id must be a positive integer"):
        Todo(id=-999, text="test")


def test_todo_init_accepts_positive_id() -> None:
    """Todo.__init__ should accept positive id values."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1
    assert todo.text == "test"


def test_todo_init_accepts_large_positive_id() -> None:
    """Todo.__init__ should accept large positive id values."""
    todo = Todo(id=999999, text="test")
    assert todo.id == 999999
    assert todo.text == "test"
