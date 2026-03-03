"""Tests for Todo.__eq__ and __hash__ methods (Issue #7080).

These tests verify that:
1. Todo equality is based on id field only
2. Todo hash is based on id field only
3. Todo instances can be used in sets and as dict keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_different_text() -> None:
    """Todo equality should be based on id field only."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy eggs")

    # Same id should be equal regardless of text
    assert todo1 == todo2


def test_todo_eq_same_id_different_done() -> None:
    """Todo equality should be based on id, ignoring done status."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    # Same id should be equal regardless of done status
    assert todo1 == todo2


def test_todo_neq_different_id() -> None:
    """Todo with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy milk")

    # Different ids should not be equal
    assert todo1 != todo2


def test_todo_hash_same_id() -> None:
    """Todo hash should be based on id field only."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy eggs")

    # Same id should have same hash
    assert hash(todo1) == hash(todo2)


def test_todo_in_set() -> None:
    """Todo instances should be addable to a set."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy eggs")

    todo_set = {todo1, todo2}

    assert len(todo_set) == 2
    assert todo1 in todo_set
    assert todo2 in todo_set


def test_todo_set_deduplication_by_id() -> None:
    """Todo instances with same id should be deduplicated in a set."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy eggs")

    # Both have same id, should deduplicate to 1 item
    todo_set = {todo1, todo2}

    assert len(todo_set) == 1


def test_todo_as_dict_key() -> None:
    """Todo instances should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy eggs")

    todo_dict = {todo1: "value1"}

    # todo2 has same id as todo1, so it should be the same key
    assert todo_dict[todo2] == "value1"


def test_todo_hash_different_id() -> None:
    """Todo with different ids should have different hashes."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy milk")

    # Different ids should typically have different hashes
    # (not guaranteed, but expected for distinct integers)
    assert hash(todo1) != hash(todo2)
