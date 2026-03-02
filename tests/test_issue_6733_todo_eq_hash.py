"""Tests for Todo.__eq__ and __hash__ methods (Issue #6733).

These tests verify that:
1. Todo objects with same id compare as equal
2. Todo objects with different ids compare as not equal
3. hash(Todo(...)) raises TypeError (mutable, unhashable)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_eq_same_id() -> None:
    """Todo objects with same id should compare as equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2


def test_todo_eq_same_id_different_fields() -> None:
    """Todo equality should be based on id field only."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    # Same id should still be equal regardless of other fields
    assert todo1 == todo2


def test_todo_eq_different_id() -> None:
    """Todo objects with different ids should compare as not equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_todo_eq_not_implemented_for_other_types() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="buy milk")

    assert todo != 1
    assert todo != "Todo(id=1, text='buy milk')"
    assert todo != {"id": 1, "text": "buy milk"}
    assert todo != None


def test_todo_hash_raises_typeerror() -> None:
    """hash(Todo) should raise TypeError because Todo is mutable."""
    todo = Todo(id=1, text="buy milk")

    with pytest.raises(TypeError):
        hash(todo)


def test_todo_not_usable_in_set() -> None:
    """Todo should not be usable in sets because it is unhashable."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy bread")

    with pytest.raises(TypeError):
        {todo1, todo2}  # noqa: B018


def test_todo_not_usable_as_dict_key() -> None:
    """Todo should not be usable as dict key because it is unhashable."""
    todo = Todo(id=1, text="buy milk")

    with pytest.raises(TypeError):
        {todo: "value"}  # noqa: B018
