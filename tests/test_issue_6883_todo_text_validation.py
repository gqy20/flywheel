"""Tests for Todo text validation (Issue #6883).

These tests verify that the Todo constructor validates the text parameter
and rejects None or non-string values, enforcing the type contract.

Acceptance criteria:
- Todo(id=1, text=None) raises ValueError
- Todo(id=1, text='valid') works as before
- Todo(id=1, text=123) raises ValueError
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_none_text() -> None:
    """Todo constructor should reject None as text value."""
    with pytest.raises(ValueError, match="text"):
        Todo(id=1, text=None)  # type: ignore[arg-type]


def test_todo_constructor_rejects_integer_text() -> None:
    """Todo constructor should reject non-string values like integers."""
    with pytest.raises(ValueError, match="text"):
        Todo(id=1, text=123)  # type: ignore[arg-type]


def test_todo_constructor_rejects_list_text() -> None:
    """Todo constructor should reject non-string values like lists."""
    with pytest.raises(ValueError, match="text"):
        Todo(id=1, text=["not", "a", "string"])  # type: ignore[arg-type]


def test_todo_constructor_accepts_valid_string_text() -> None:
    """Todo constructor should accept valid string text (baseline)."""
    todo = Todo(id=1, text="valid text")
    assert todo.text == "valid text"


def test_todo_constructor_accepts_empty_string_text() -> None:
    """Todo constructor should accept empty string (different from None)."""
    todo = Todo(id=1, text="")
    assert todo.text == ""
