"""Tests for Todo.__eq__ and __hash__ support (Issue #5958).

This module tests the equality and hashing behavior of Todo objects.
Equality is based on the 'id' field (unique identifier).
Hashing allows Todo objects to be used in sets and as dict keys.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id() -> None:
    """Two Todo objects with the same id should be equal."""
    todo1 = Todo(id=1, text="task a")
    todo2 = Todo(id=1, text="task a")
    assert todo1 == todo2


def test_todo_equality_same_id_different_text() -> None:
    """Two Todo objects with the same id but different text should be equal.

    Equality is based on id only, since id is the unique identifier.
    """
    todo1 = Todo(id=1, text="task a")
    todo2 = Todo(id=1, text="task b")
    assert todo1 == todo2


def test_todo_inequality_different_id() -> None:
    """Two Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="task a")
    todo2 = Todo(id=2, text="task a")
    assert todo1 != todo2


def test_todo_hash_allows_set_deduplication() -> None:
    """Todo objects should be hashable and work with sets for deduplication."""
    todo1 = Todo(id=1, text="task a")
    todo2 = Todo(id=1, text="task b")  # Same id, different text
    todo3 = Todo(id=2, text="task c")

    # Set should deduplicate based on hash/equality (by id)
    todo_set = {todo1, todo2, todo3}
    assert len(todo_set) == 2  # todo1 and todo2 are considered equal


def test_todo_hash_allows_dict_keys() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="task a")
    todo2 = Todo(id=2, text="task b")

    todo_dict = {todo1: "first", todo2: "second"}
    assert todo_dict[todo1] == "first"
    assert todo_dict[todo2] == "second"


def test_todo_hash_consistency() -> None:
    """Hash should be consistent for the same Todo object."""
    todo = Todo(id=1, text="task")
    hash1 = hash(todo)
    hash2 = hash(todo)
    assert hash1 == hash2


def test_todo_hash_equal_objects_equal_hashes() -> None:
    """Equal objects should have equal hashes (hash contract)."""
    todo1 = Todo(id=1, text="task a")
    todo2 = Todo(id=1, text="task b")
    # If todo1 == todo2, then hash(todo1) == hash(todo2)
    assert todo1 == todo2
    assert hash(todo1) == hash(todo2)
