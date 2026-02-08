"""Tests for Todo.rename() type validation (Issue #2222).

These tests verify that:
1. Todo.rename() validates that text is a string before calling strip()
2. Non-string inputs raise TypeError with clear message
3. Existing rename() functionality continues to work
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_rename_rejects_none() -> None:
    """Bug #2222: Todo.rename() should raise TypeError for None input."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at

    # None should raise TypeError, not AttributeError
    with pytest.raises(TypeError, match="Todo text must be a string"):
        todo.rename(None)

    # Verify state unchanged after failed validation
    assert todo.text == "original"
    assert todo.updated_at == original_updated_at


def test_todo_rename_rejects_integer() -> None:
    """Bug #2222: Todo.rename() should raise TypeError for integer input."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at

    # Integer should raise TypeError
    with pytest.raises(TypeError, match="Todo text must be a string"):
        todo.rename(123)

    # Verify state unchanged
    assert todo.text == "original"
    assert todo.updated_at == original_updated_at


def test_todo_rename_rejects_list() -> None:
    """Bug #2222: Todo.rename() should raise TypeError for list input."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at

    # List should raise TypeError
    with pytest.raises(TypeError, match="Todo text must be a string"):
        todo.rename(["list", "of", "items"])

    # Verify state unchanged
    assert todo.text == "original"
    assert todo.updated_at == original_updated_at


def test_todo_rename_rejects_dict() -> None:
    """Bug #2222: Todo.rename() should raise TypeError for dict input."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at

    # Dict should raise TypeError
    with pytest.raises(TypeError, match="Todo text must be a string"):
        todo.rename({"text": "not a string"})

    # Verify state unchanged
    assert todo.text == "original"
    assert todo.updated_at == original_updated_at


def test_todo_rename_rejects_boolean() -> None:
    """Bug #2222: Todo.rename() should raise TypeError for boolean input."""
    todo = Todo(id=1, text="original")
    original_updated_at = todo.updated_at

    # Boolean should raise TypeError (even though bool is subclass of int in Python)
    with pytest.raises(TypeError, match="Todo text must be a string"):
        todo.rename(True)

    # Verify state unchanged
    assert todo.text == "original"
    assert todo.updated_at == original_updated_at


def test_todo_rename_accepts_valid_string() -> None:
    """Bug #2222: Todo.rename() should still work with valid string input."""
    todo = Todo(id=1, text="original")

    # Valid string should work normally
    todo.rename("new text")
    assert todo.text == "new text"


def test_todo_rename_strips_whitespace() -> None:
    """Bug #2222: Todo.rename() should still strip whitespace from valid strings."""
    todo = Todo(id=1, text="original")

    # Whitespace should still be stripped
    todo.rename("  new text  ")
    assert todo.text == "new text"
