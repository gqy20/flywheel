"""Tests for Todo id validation (Issue #5446).

Bug: Todo constructor did not validate that id is a positive integer.
Fix: Added validation in __post_init__ to ensure id >= 1.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_rejects_negative_id() -> None:
    """Todo(id=-1, ...) should raise ValueError."""
    with pytest.raises(ValueError, match="id must be a positive integer"):
        Todo(id=-1, text="test")


def test_todo_rejects_zero_id() -> None:
    """Todo(id=0, ...) should raise ValueError (ids start from 1)."""
    with pytest.raises(ValueError, match="id must be a positive integer"):
        Todo(id=0, text="test")


def test_todo_accepts_positive_id() -> None:
    """Todo(id=1, ...) should create successfully."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1
    assert todo.text == "test"


def test_todo_accepts_large_positive_id() -> None:
    """Todo should accept any positive integer id."""
    todo = Todo(id=999999, text="large id test")
    assert todo.id == 999999
