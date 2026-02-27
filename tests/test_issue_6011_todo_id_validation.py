"""Regression tests for issue #6011: Todo constructor must validate ID > 0."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_negative_id() -> None:
    """Bug #6011: Todo constructor should reject negative IDs."""
    with pytest.raises(ValueError, match="id"):
        Todo(id=-1, text="test")


def test_todo_constructor_rejects_zero_id() -> None:
    """Bug #6011: Todo constructor should reject zero ID."""
    with pytest.raises(ValueError, match="id"):
        Todo(id=0, text="test")


def test_todo_from_dict_rejects_negative_id() -> None:
    """Bug #6011: Todo.from_dict should reject negative IDs."""
    with pytest.raises(ValueError, match="id"):
        Todo.from_dict({"id": -1, "text": "test"})


def test_todo_from_dict_rejects_zero_id() -> None:
    """Bug #6011: Todo.from_dict should reject zero ID."""
    with pytest.raises(ValueError, match="id"):
        Todo.from_dict({"id": 0, "text": "test"})


def test_todo_constructor_accepts_positive_id() -> None:
    """Bug #6011: Positive IDs should still work correctly."""
    todo = Todo(id=1, text="test")
    assert todo.id == 1
    assert todo.text == "test"


def test_todo_from_dict_accepts_positive_id() -> None:
    """Bug #6011: Positive IDs should still work via from_dict."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.id == 1
    assert todo.text == "test"
