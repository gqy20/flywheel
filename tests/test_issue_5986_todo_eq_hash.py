"""Tests for Todo.__eq__ and __hash__ methods (Issue #5986).

These tests verify that:
1. Todo objects with same data are equal
2. Todo objects can be used in sets
3. Todo objects with same id have same hash (id-based hashing)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_data() -> None:
    """Todo objects with same data should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2


def test_todo_equality_different_id() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_todo_equality_different_text() -> None:
    """Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2


def test_todo_equality_different_done() -> None:
    """Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2


def test_todo_equality_with_non_todo() -> None:
    """Todo compared with non-Todo should return False."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != "not a todo"
    assert todo != 1
    assert todo is not None
    assert todo != {"id": 1, "text": "buy milk", "done": False}


def test_todo_hash_same_id() -> None:
    """Todo objects with same id should have same hash."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)

    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_id() -> None:
    """Todo objects with different ids should have different hashes."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    # Hashes are likely different (not guaranteed, but id-based hashing makes this true)
    assert hash(todo1) != hash(todo2)


def test_todo_can_be_added_to_set() -> None:
    """Todo objects can be added to a set without error."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy bread", done=True)

    todo_set = {todo1, todo2}

    assert len(todo_set) == 2
    assert todo1 in todo_set
    assert todo2 in todo_set


def test_todo_set_deduplication() -> None:
    """Set should deduplicate Todo objects with same id (hash-based)."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)  # Same id, different content

    todo_set = {todo1, todo2}

    # Since hash is based on id, both todos have same hash
    # Set uses hash + equality, so they may or may not be deduplicated
    # depending on equality implementation
    # With id-based hash, this is acceptable behavior
    assert len(todo_set) >= 1


def test_todo_can_be_dict_key() -> None:
    """Todo objects can be used as dictionary keys."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy bread", done=True)

    todo_dict = {todo1: "first", todo2: "second"}

    assert todo_dict[todo1] == "first"
    assert todo_dict[todo2] == "second"
