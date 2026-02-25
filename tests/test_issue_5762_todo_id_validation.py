"""Tests for Todo id validation (Issue #5762).

These tests verify that:
1. Todo constructor validates id is a non-negative integer
2. Todo(id=-1, text='x') raises ValueError
3. Todo(id=0, text='x') succeeds (0 is valid)
4. Todo(id=1, text='x') succeeds
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_negative_id_raises_value_error() -> None:
    """Todo(id=-1, text='x') should raise ValueError with message about non-negative id."""
    with pytest.raises(ValueError, match="non-negative"):
        Todo(id=-1, text="x")


def test_todo_zero_id_succeeds() -> None:
    """Todo(id=0, text='x') should succeed (0 is valid)."""
    todo = Todo(id=0, text="x")
    assert todo.id == 0
    assert todo.text == "x"


def test_todo_positive_id_succeeds() -> None:
    """Todo(id=1, text='x') should succeed."""
    todo = Todo(id=1, text="x")
    assert todo.id == 1
    assert todo.text == "x"


def test_todo_large_positive_id_succeeds() -> None:
    """Todo with large positive id should succeed."""
    todo = Todo(id=999999, text="large id task")
    assert todo.id == 999999
