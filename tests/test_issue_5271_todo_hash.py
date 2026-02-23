"""Tests for Todo.__hash__ method (Issue #5271).

These tests verify that:
1. Todo objects are explicitly unhashable (since Todo is mutable)
2. Attempting to hash a Todo raises TypeError with clear message
3. Todo cannot be added to sets or used as dict keys
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_is_unhashable() -> None:
    """Todo should be unhashable because it's a mutable dataclass."""
    todo = Todo(id=1, text="test todo")

    with pytest.raises(TypeError) as exc_info:
        hash(todo)

    # Should raise TypeError with 'unhashable type' message
    assert "unhashable" in str(exc_info.value).lower()


def test_todo_cannot_be_added_to_set() -> None:
    """Todo should not be usable in sets because it's mutable."""
    todo = Todo(id=1, text="test todo")

    with pytest.raises(TypeError) as exc_info:
        {todo}  # noqa: B018

    assert "unhashable" in str(exc_info.value).lower()


def test_todo_cannot_be_dict_key() -> None:
    """Todo should not be usable as dict key because it's mutable."""
    todo = Todo(id=1, text="test todo")

    with pytest.raises(TypeError) as exc_info:
        {todo: "value"}  # noqa: B018

    assert "unhashable" in str(exc_info.value).lower()


def test_todo_hash_is_none() -> None:
    """Todo.__hash__ should be None to explicitly mark it as unhashable."""
    # This explicitly marks the class as intentionally unhashable
    # rather than implicitly unhashable due to mutable dataclass
    assert Todo.__hash__ is None
