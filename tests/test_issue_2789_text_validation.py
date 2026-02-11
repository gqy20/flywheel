"""Regression tests for Issue #2789: Duplicate strip() logic and inconsistent validation.

This test file ensures that:
1. Todo.__post_init__() validates text properly (currently doesn't)
2. Todo.from_dict() validates text properly (currently only checks type)
3. Both methods strip leading/trailing whitespace like rename() does
4. No duplicate strip/validation logic across methods
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_init_with_whitespace_only_text_raises_error() -> None:
    """Creating Todo with whitespace-only text should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="   ")


def test_init_with_empty_text_raises_error() -> None:
    """Creating Todo with empty string should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo(id=1, text="")


def test_init_strips_leading_trailing_whitespace() -> None:
    """Creating Todo should strip leading/trailing whitespace like rename() does."""
    todo = Todo(id=1, text="  Buy milk  ")
    assert todo.text == "Buy milk"


def test_rename_whitespace_only_raises_error() -> None:
    """rename() with whitespace-only text should raise ValueError."""
    todo = Todo(id=1, text="Original")
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        todo.rename("   ")


def test_rename_strips_leading_trailing_whitespace() -> None:
    """rename() should strip leading/trailing whitespace."""
    todo = Todo(id=1, text="Original")
    todo.rename("  Buy milk  ")
    assert todo.text == "Buy milk"


def test_from_dict_with_whitespace_only_text_raises_error() -> None:
    """from_dict() with whitespace-only text should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": "   "})


def test_from_dict_with_empty_text_raises_error() -> None:
    """from_dict() with empty string should raise ValueError."""
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_from_dict_strips_leading_trailing_whitespace() -> None:
    """from_dict() should strip leading/trailing whitespace."""
    todo = Todo.from_dict({"id": 1, "text": "  Buy milk  "})
    assert todo.text == "Buy milk"


def test_init_with_normal_text() -> None:
    """Creating Todo with normal text should work fine."""
    todo = Todo(id=1, text="Buy milk")
    assert todo.text == "Buy milk"


def test_from_dict_with_normal_text() -> None:
    """from_dict() with normal text should work fine."""
    todo = Todo.from_dict({"id": 1, "text": "Buy milk"})
    assert todo.text == "Buy milk"
