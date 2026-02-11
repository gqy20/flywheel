"""Tests for Todo.__eq__ and __hash__ methods (Issue #2730).

These tests verify that:
1. Todo objects with same id are considered equal
2. Todo objects with different ids are not equal
3. Todo can be used in sets for deduplication
4. Todo can be used as dict keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id() -> None:
    """Two Todo objects with same id should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    assert todo1 == todo2


def test_todo_eq_different_id() -> None:
    """Two Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text", done=False)
    todo2 = Todo(id=2, text="same text", done=False)

    assert todo1 != todo2


def test_todo_eq_self() -> None:
    """Todo should equal itself."""
    todo = Todo(id=1, text="buy milk", done=False)
    assert todo == todo


def test_todo_eq_non_todo() -> None:
    """Todo should not equal non-Todo objects."""
    todo = Todo(id=1, text="buy milk", done=False)
    assert todo != 1
    assert todo != "Todo(id=1)"
    assert todo is not None


def test_todo_hash_consistent() -> None:
    """hash(Todo) should be consistent for same id."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_id() -> None:
    """hash(Todo) should differ for different ids."""
    todo1 = Todo(id=1, text="same text", done=False)
    todo2 = Todo(id=2, text="same text", done=False)

    assert hash(todo1) != hash(todo2)


def test_todo_in_set() -> None:
    """Todo should be usable in a set."""
    todo1 = Todo(id=1, text="task one", done=False)
    todo2 = Todo(id=2, text="task two", done=True)
    todo3 = Todo(id=1, text="duplicate id", done=False)  # Same id as todo1

    todo_set = {todo1, todo2, todo3}

    # Set should deduplicate by id
    assert len(todo_set) == 2

    # Check membership by id
    assert Todo(id=1, text="any text") in todo_set
    assert Todo(id=2, text="any text") in todo_set
    assert Todo(id=3, text="any text") not in todo_set


def test_todo_as_dict_key() -> None:
    """Todo should be usable as a dict key."""
    todo1 = Todo(id=1, text="task one", done=False)
    todo2 = Todo(id=2, text="task two", done=True)
    todo3 = Todo(id=1, text="duplicate id", done=False)  # Same id as todo1

    todo_dict = {todo1: "first", todo2: "second"}

    # Lookup by id should work
    assert todo_dict[Todo(id=1, text="any text")] == "first"
    assert todo_dict[Todo(id=2, text="any text")] == "second"

    # todo3 should map to same value as todo1 (same id)
    assert todo_dict[todo3] == "first"
