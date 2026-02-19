"""Tests for Todo.__eq__ and __hash__ methods (Issue #4537).

These tests verify that:
1. Todo objects with same id and text are equal
2. Todo objects with different id or text are not equal
3. hash(Todo) is consistent for same id
4. Todo objects can be added to sets and deduplicated by id
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_and_text_returns_true() -> None:
    """Todo(id=1, text='a') == Todo(id=1, text='a') should return True."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")
    assert todo1 == todo2


def test_todo_eq_different_id_returns_false() -> None:
    """Todo(id=1, text='a') != Todo(id=2, text='a') should return True."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")
    assert todo1 != todo2


def test_todo_eq_different_text_returns_false() -> None:
    """Todo(id=1, text='a') != Todo(id=1, text='b') should return True."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    assert todo1 != todo2


def test_todo_eq_different_done_returns_false() -> None:
    """Todos with same id but different done status should not be equal."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=True)
    assert todo1 != todo2


def test_todo_eq_different_type_returns_false() -> None:
    """Todo comparison with non-Todo type should return False."""
    todo = Todo(id=1, text="a")
    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "a"}


def test_todo_hash_consistent_for_same_id_and_text() -> None:
    """hash(Todo) should be consistent for objects with same id and text."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")
    assert hash(todo1) == hash(todo2)


def test_todo_hash_consistent_for_same_id_different_text() -> None:
    """hash(Todo) should be consistent for objects with same id (regardless of text)."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    # Hash is based only on id for deduplication purposes
    assert hash(todo1) == hash(todo2)


def test_todo_can_be_added_to_set() -> None:
    """Todo objects should be addable to a set."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="b")
    todo_set = {todo1, todo2}
    assert len(todo_set) == 2
    assert todo1 in todo_set
    assert todo2 in todo_set


def test_todo_set_deduplication_by_id() -> None:
    """Todo objects with same id should be deduplicated in a set."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")
    todo_set = {todo1, todo2}
    # Should have only 1 item since they have same id and text
    assert len(todo_set) == 1


def test_todo_set_keeps_different_text_same_id() -> None:
    """Todo objects with same id but different text remain distinct in a set.

    Since __eq__ compares id, text, and done, objects with different text
    are not equal, even though they have the same hash (based on id only).
    Python sets use both hash AND equality, so both objects are kept.
    """
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    todo_set = {todo1, todo2}
    # Both remain because they are not equal (different text)
    assert len(todo_set) == 2
    assert todo1 in todo_set
    assert todo2 in todo_set


def test_todo_can_be_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="b")
    todo_dict = {todo1: "first", todo2: "second"}
    assert todo_dict[todo1] == "first"
    assert todo_dict[todo2] == "second"


def test_todo_dict_key_lookup_by_equivalent() -> None:
    """Todo dict lookup should work with an equivalent Todo object."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")
    todo_dict = {todo1: "value"}
    assert todo_dict[todo2] == "value"


def test_todo_eq_reflexive() -> None:
    """Todo equality should be reflexive (x == x)."""
    todo = Todo(id=1, text="a")
    assert todo == todo


def test_todo_eq_symmetric() -> None:
    """Todo equality should be symmetric (x == y implies y == x)."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")
    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_eq_transitive() -> None:
    """Todo equality should be transitive (x == y and y == z implies x == z)."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")
    todo3 = Todo(id=1, text="a")
    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3
