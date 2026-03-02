"""Tests for Todo.__eq__ and __hash__ methods (Issue #6733).

These tests verify that:
1. Todo objects with same id compare as equal
2. Todo objects with different ids compare as not equal
3. Todo is unhashable (raises TypeError) since it's mutable
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_eq_same_id_returns_true() -> None:
    """Todo objects with same id should compare as equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2


def test_todo_eq_same_id_different_text_returns_true() -> None:
    """Todo equality should be based on id field only."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="different text")

    # Same id means equal, even with different text
    assert todo1 == todo2


def test_todo_eq_different_id_returns_false() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_todo_eq_different_done_returns_true() -> None:
    """Todo equality should be based on id, not done status."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    # Same id means equal, even with different done status
    assert todo1 == todo2


def test_todo_not_equal_to_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="buy milk")

    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk"}
    assert todo is not None


def test_todo_hash_raises_type_error() -> None:
    """Todo should be unhashable since it's mutable."""
    todo = Todo(id=1, text="buy milk")

    with pytest.raises(TypeError):
        hash(todo)


def test_todo_not_usable_in_set() -> None:
    """Todo should not be usable in a set since it's unhashable."""
    todo = Todo(id=1, text="buy milk")

    with pytest.raises(TypeError):
        {todo}  # noqa: B018


def test_todo_not_usable_as_dict_key() -> None:
    """Todo should not be usable as a dict key since it's unhashable."""
    todo = Todo(id=1, text="buy milk")

    with pytest.raises(TypeError):
        {todo: "value"}  # noqa: B018
