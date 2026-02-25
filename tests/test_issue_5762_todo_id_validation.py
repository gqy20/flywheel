"""Tests for Todo id validation (Issue #5762).

These tests verify that:
1. Todo constructor validates id is a non-negative integer
2. Negative id values raise ValueError
3. Zero and positive id values are accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_negative_id_raises_value_error() -> None:
    """Todo(id=-1, text='x') should raise ValueError about non-negative id."""
    with pytest.raises(ValueError) as exc_info:
        Todo(id=-1, text="x")

    assert "non-negative" in str(exc_info.value).lower()


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
    """Todo should accept large positive id values."""
    todo = Todo(id=999999, text="large id task")
    assert todo.id == 999999


def test_todo_multiple_negative_ids_rejected() -> None:
    """Todo should reject various negative id values."""
    for negative_id in [-1, -100, -999]:
        with pytest.raises(ValueError) as exc_info:
            Todo(id=negative_id, text="test")
        assert "non-negative" in str(exc_info.value).lower()
