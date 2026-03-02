"""Tests for Todo __eq__ and __hash__ methods (Issue #6733).

These tests verify that:
1. Todo objects with the same id compare as equal
2. Todo objects with different ids compare as not equal
3. Todo objects are unhashable (mutable, cannot be used in sets/dicts)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_eq_same_id_same_text() -> None:
    """Todo objects with same id and text should compare as equal."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy milk")
    assert todo1 == todo2


def test_todo_eq_same_id_different_text() -> None:
    """Todo objects with same id should compare as equal regardless of text.

    The id field is the primary identifier for equality comparison.
    """
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="different text")
    assert todo1 == todo2


def test_todo_eq_different_id_same_text() -> None:
    """Todo objects with different ids should compare as not equal."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy milk")
    assert todo1 != todo2


def test_todo_eq_different_id_different_text() -> None:
    """Todo objects with different ids and text should compare as not equal."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy bread")
    assert todo1 != todo2


def test_todo_eq_same_id_different_done() -> None:
    """Todo objects with same id should compare as equal regardless of done state."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)
    assert todo1 == todo2


def test_todo_eq_reflexive() -> None:
    """A Todo should equal itself (reflexive property)."""
    todo = Todo(id=1, text="buy milk")
    assert todo == todo


def test_todo_eq_symmetric() -> None:
    """If todo1 == todo2, then todo2 == todo1 (symmetric property)."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy milk")
    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_eq_transitive() -> None:
    """If todo1 == todo2 and todo2 == todo3, then todo1 == todo3."""
    todo1 = Todo(id=1, text="text")
    todo2 = Todo(id=1, text="text")
    todo3 = Todo(id=1, text="text")
    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3


def test_todo_eq_with_non_todo() -> None:
    """Todo should not equal non-Todo objects."""
    todo = Todo(id=1, text="buy milk")
    assert todo != "buy milk"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk"}
    assert todo is not None


def test_todo_hash_raises_type_error() -> None:
    """Todo objects should be unhashable because they are mutable."""
    todo = Todo(id=1, text="buy milk")
    with pytest.raises(TypeError):
        hash(todo)


def test_todo_not_usable_in_set() -> None:
    """Todo objects should not be usable in sets because they are unhashable."""
    todo = Todo(id=1, text="buy milk")
    with pytest.raises(TypeError):
        {todo}  # noqa: B018


def test_todo_not_usable_as_dict_key() -> None:
    """Todo objects should not be usable as dict keys because they are unhashable."""
    todo = Todo(id=1, text="buy milk")
    with pytest.raises(TypeError):
        {todo: "value"}  # noqa: B018
