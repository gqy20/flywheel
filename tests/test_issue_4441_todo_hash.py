"""Tests for Todo hash support (Issue #4441).

These tests verify that:
1. Todo objects with the same id produce consistent hash values
2. Todo objects can be used in sets for deduplication
3. Todo objects can be used as dictionary keys
4. Hash is based on id field only (not other fields)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_hash_consistent_for_same_id() -> None:
    """hash(Todo) should return same value for same id, regardless of other fields."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    assert hash(todo1) == hash(todo2), (
        f"Todos with same id should have same hash: {hash(todo1)} != {hash(todo2)}"
    )


def test_todo_hash_different_for_different_id() -> None:
    """hash(Todo) should return different values for different ids."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task two")

    assert hash(todo1) != hash(todo2), (
        f"Todos with different ids should have different hashes: {hash(todo1)} == {hash(todo2)}"
    )


def test_todo_in_set_works() -> None:
    """Todo objects should work in sets for deduplication by id.

    Acceptance criterion: len({Todo(id=1), Todo(id=1)}) == 1
    """
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy milk")

    # Set should deduplicate by id (acceptance criterion)
    todo_set = {todo1, todo2}
    assert len(todo_set) == 1, (
        f"Set should deduplicate Todos by id: expected 1, got {len(todo_set)}"
    )


def test_todo_as_dict_key_works() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo = Todo(id=1, text="important task")
    todo_dict = {todo: "metadata"}

    # Should be able to retrieve by the same todo
    assert todo_dict[todo] == "metadata"

    # Should be able to use another todo with same id (if hash matches)
    todo_same_id = Todo(id=1, text="important task")
    # Note: dict lookup uses both hash and eq, so this tests hashability
    assert hash(todo) == hash(todo_same_id)


def test_todo_hash_is_stable() -> None:
    """hash(Todo) should be stable and not change when other fields change."""
    todo = Todo(id=42, text="original text")
    original_hash = hash(todo)

    # Modify text (should not affect hash since it's id-based)
    todo.text = "modified text"
    assert hash(todo) == original_hash, (
        f"Hash should not change when text changes: {original_hash} != {hash(todo)}"
    )

    # Modify done status (should not affect hash)
    todo.done = True
    assert hash(todo) == original_hash, (
        f"Hash should not change when done changes: {original_hash} != {hash(todo)}"
    )


def test_todo_hash_with_negative_id() -> None:
    """hash(Todo) should work with negative ids."""
    todo = Todo(id=-1, text="negative id task")
    # Should not raise and should be consistent
    hash_value = hash(todo)
    assert isinstance(hash_value, int)


def test_todo_hash_with_large_id() -> None:
    """hash(Todo) should work with large ids."""
    todo = Todo(id=999999999, text="large id task")
    hash_value = hash(todo)
    assert isinstance(hash_value, int)
