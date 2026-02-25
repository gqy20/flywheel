"""Tests for Todo.rename() type validation (Issue #5760).

These tests verify that:
1. Todo.rename() raises TypeError when passed None
2. Todo.rename() raises TypeError when passed non-string types (int, list, etc.)
3. Todo.rename() still works correctly with valid string input
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_rename_rejects_none_argument() -> None:
    """rename(None) should raise TypeError with clear message."""
    todo = Todo(id=1, text="original text")
    with pytest.raises(TypeError) as exc_info:
        todo.rename(None)
    assert "text must be a string" in str(exc_info.value)


def test_rename_rejects_integer_argument() -> None:
    """rename(123) should raise TypeError with clear message."""
    todo = Todo(id=1, text="original text")
    with pytest.raises(TypeError) as exc_info:
        todo.rename(123)
    assert "text must be a string" in str(exc_info.value)


def test_rename_rejects_list_argument() -> None:
    """rename(['not', 'a', 'string']) should raise TypeError with clear message."""
    todo = Todo(id=1, text="original text")
    with pytest.raises(TypeError) as exc_info:
        todo.rename(["not", "a", "string"])
    assert "text must be a string" in str(exc_info.value)


def test_rename_rejects_dict_argument() -> None:
    """rename({'text': 'value'}) should raise TypeError with clear message."""
    todo = Todo(id=1, text="original text")
    with pytest.raises(TypeError) as exc_info:
        todo.rename({"text": "value"})
    assert "text must be a string" in str(exc_info.value)


def test_rename_accepts_valid_string() -> None:
    """rename('valid text') should work correctly."""
    todo = Todo(id=1, text="original text")
    todo.rename("new valid text")
    assert todo.text == "new valid text"


def test_rename_strips_whitespace() -> None:
    """rename('  text  ') should strip leading/trailing whitespace."""
    todo = Todo(id=1, text="original text")
    todo.rename("  trimmed text  ")
    assert todo.text == "trimmed text"


def test_rename_rejects_empty_after_strip() -> None:
    """rename('   ') should raise ValueError (existing behavior)."""
    todo = Todo(id=1, text="original text")
    with pytest.raises(ValueError) as exc_info:
        todo.rename("   ")
    assert "cannot be empty" in str(exc_info.value)
