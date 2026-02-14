"""Tests for Todo.__post_init__ validation (Issue #3129).

These tests verify that:
1. Todo.__post_init__ rejects empty text
2. Todo.__post_init__ rejects negative id
3. Todo.__post_init__ rejects whitespace-only text
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_post_init_rejects_empty_text() -> None:
    """Todo(id=1, text='') should raise ValueError."""
    with pytest.raises(ValueError, match="text"):
        Todo(id=1, text="")


def test_post_init_rejects_negative_id() -> None:
    """Todo(id=-1, text='valid') should raise ValueError."""
    with pytest.raises(ValueError, match="id"):
        Todo(id=-1, text="valid")


def test_post_init_rejects_whitespace_text() -> None:
    """Todo(id=1, text='  ') should raise ValueError."""
    with pytest.raises(ValueError, match="text"):
        Todo(id=1, text="  ")


def test_post_init_accepts_valid_todo() -> None:
    """Todo with valid id and text should be created successfully."""
    todo = Todo(id=1, text="valid task")
    assert todo.id == 1
    assert todo.text == "valid task"


def test_post_init_accepts_zero_id() -> None:
    """Todo(id=0, text='valid') should be valid (zero is non-negative)."""
    todo = Todo(id=0, text="valid")
    assert todo.id == 0
    assert todo.text == "valid"
