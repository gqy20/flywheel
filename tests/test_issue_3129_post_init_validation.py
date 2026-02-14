"""Tests for Todo.__post_init__ validation (Issue #3129).

These tests verify that __post_init__ validates:
1. id must be non-negative
2. text must not be empty after stripping
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_post_init_rejects_negative_id() -> None:
    """Todo(id=-1, text='x') should raise ValueError."""
    with pytest.raises(ValueError, match="id"):
        Todo(id=-1, text="valid text")


def test_post_init_rejects_empty_text() -> None:
    """Todo(id=1, text='') should raise ValueError."""
    with pytest.raises(ValueError, match=r"text.*empty"):
        Todo(id=1, text="")


def test_post_init_rejects_whitespace_text() -> None:
    """Todo(id=1, text='  ') should raise ValueError."""
    with pytest.raises(ValueError, match=r"text.*empty"):
        Todo(id=1, text="   ")


def test_post_init_accepts_valid_input() -> None:
    """Valid Todo should be created without error."""
    todo = Todo(id=1, text="valid task")
    assert todo.id == 1
    assert todo.text == "valid task"


def test_post_init_accepts_zero_id() -> None:
    """id=0 should be valid (non-negative)."""
    todo = Todo(id=0, text="task with zero id")
    assert todo.id == 0


def test_post_init_accepts_text_with_leading_trailing_spaces() -> None:
    """Text with content but spaces should be accepted (stripped)."""
    todo = Todo(id=1, text="  valid task  ")
    # Text should be stripped, similar to rename behavior
    assert todo.text == "valid task"
