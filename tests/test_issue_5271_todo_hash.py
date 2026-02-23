"""Tests for Todo.__hash__ method (Issue #5271).

These tests verify that:
1. Todo objects are explicitly unhashable (since Todo is mutable)
2. Attempting to use Todo in set/dict raises clear TypeError
3. The error message is clear and Python-standard
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_is_unhashable() -> None:
    """Todo objects should not be hashable since they are mutable."""
    todo = Todo(id=1, text="test task")

    with pytest.raises(TypeError) as exc_info:
        hash(todo)

    # Should raise standard Python error for unhashable types
    assert "unhashable" in str(exc_info.value).lower()


def test_todo_cannot_be_added_to_set() -> None:
    """Adding Todo to a set should raise TypeError."""
    todo = Todo(id=1, text="test task")

    with pytest.raises(TypeError) as exc_info:
        {todo}  # noqa: B018

    assert "unhashable" in str(exc_info.value).lower()


def test_todo_cannot_be_used_as_dict_key() -> None:
    """Using Todo as dict key should raise TypeError."""
    todo = Todo(id=1, text="test task")

    with pytest.raises(TypeError) as exc_info:
        {todo: "value"}  # noqa: B018

    assert "unhashable" in str(exc_info.value).lower()


def test_todo_hash_is_none() -> None:
    """Todo class should have __hash__ = None (unhashable)."""
    # This is Python's standard way to mark a class as unhashable
    assert Todo.__hash__ is None


def test_todo_set_with_multiple_todos_raises_immediately() -> None:
    """Creating a set with multiple Todos should raise on first insertion."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task two")

    # Should fail on set creation, not on adding second item
    with pytest.raises(TypeError) as exc_info:
        {todo1, todo2}  # noqa: B018

    assert "unhashable" in str(exc_info.value).lower()
