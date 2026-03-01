"""Tests for issue #6606: Todo __eq__ and __hash__ methods."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_objects_with_same_id_are_equal() -> None:
    """Issue #6606: Todo objects with the same id should be equal."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="b", done=True)

    # Same id should be equal regardless of other fields
    assert todo1 == todo2


def test_todo_objects_with_different_id_are_not_equal() -> None:
    """Issue #6606: Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")

    # Different ids should not be equal even with same text
    assert todo1 != todo2


def test_todo_objects_can_be_used_in_set() -> None:
    """Issue #6606: Todo objects should be hashable and usable in sets."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")  # Same id as todo1
    todo3 = Todo(id=2, text="c")

    todo_set = {todo1, todo2, todo3}

    # Set should deduplicate by id
    assert len(todo_set) == 2


def test_todo_objects_can_be_used_as_dict_keys() -> None:
    """Issue #6606: Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")  # Same id as todo1
    todo3 = Todo(id=2, text="c")

    todo_dict = {todo1: "first", todo2: "second", todo3: "third"}

    # Dict should deduplicate by id
    assert len(todo_dict) == 2
    # The second value should override the first for same id
    assert todo_dict[todo1] == "second"


def test_todo_hash_consistency() -> None:
    """Issue #6606: Hash should be consistent for same id."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")

    # Same id should produce same hash
    assert hash(todo1) == hash(todo2)


def test_todo_hash_differs_for_different_ids() -> None:
    """Issue #6606: Hash should differ for different ids."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")

    # Different ids should produce different hashes
    assert hash(todo1) != hash(todo2)
