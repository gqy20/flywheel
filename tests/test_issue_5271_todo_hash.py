"""Tests for Todo.__hash__ method (Issue #5271).

These tests verify that:
1. Todo objects explicitly disable hashing with __hash__ = None
2. The class source code contains an explicit __hash__ = None declaration
3. Attempting to hash a Todo raises TypeError with 'unhashable type' message
4. Attempting to use Todo in a set raises TypeError
5. Attempting to use Todo as a dict key raises TypeError
"""

from __future__ import annotations

import inspect

import pytest

from flywheel.todo import Todo


def test_todo_has_hash_none() -> None:
    """Todo class should have __hash__ set to None explicitly."""
    assert Todo.__hash__ is None, "Todo.__hash__ should be None for mutable objects"


def test_todo_hash_declared_in_source() -> None:
    """Todo class should have an explicit __hash__ = None declaration in source."""
    source = inspect.getsource(Todo)
    assert "__hash__ = None" in source, (
        "Todo class should explicitly declare __hash__ = None for clarity"
    )


def test_todo_hash_raises_type_error() -> None:
    """Calling hash() on a Todo should raise TypeError."""
    todo = Todo(id=1, text="test todo")

    with pytest.raises(TypeError) as exc_info:
        hash(todo)

    # Error message should indicate unhashable type
    error_msg = str(exc_info.value)
    assert "unhashable" in error_msg.lower(), f"Expected 'unhashable' in error: {error_msg}"


def test_todo_in_set_raises_type_error() -> None:
    """Adding a Todo to a set should raise TypeError."""
    todo = Todo(id=1, text="test todo")

    with pytest.raises(TypeError) as exc_info:
        {todo}  # noqa: B018

    error_msg = str(exc_info.value)
    assert "unhashable" in error_msg.lower()


def test_todo_as_dict_key_raises_type_error() -> None:
    """Using a Todo as a dict key should raise TypeError."""
    todo = Todo(id=1, text="test todo")
    value = "some value"

    with pytest.raises(TypeError) as exc_info:
        {todo: value}  # noqa: B018

    error_msg = str(exc_info.value)
    assert "unhashable" in error_msg.lower()


def test_todo_multiple_objects_unhashable() -> None:
    """Multiple Todo objects should all be unhashable."""
    todo1 = Todo(id=1, text="first todo")
    todo2 = Todo(id=2, text="second todo", done=True)

    for todo in [todo1, todo2]:
        with pytest.raises(TypeError):
            hash(todo)

        with pytest.raises(TypeError):
            {todo}  # noqa: B018
