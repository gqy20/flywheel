"""Tests for Todo id validation (Issue #5762).

These tests verify that:
1. Todo constructor validates id is a non-negative integer
2. Negative ids raise ValueError
3. Zero is a valid id
4. Positive integers are valid ids
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_negative_id_raises_value_error() -> None:
    """Todo(id=-1, text='x') should raise ValueError."""
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


def test_todo_large_negative_id_raises_value_error() -> None:
    """Todo with large negative id should also raise ValueError."""
    with pytest.raises(ValueError, match="non-negative"):
        Todo(id=-99999, text="test")
