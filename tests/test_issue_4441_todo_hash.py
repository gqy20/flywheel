"""Tests for Todo hash support (Issue #4441).

These tests verify that:
1. Todo objects are hashable based on their id
2. Todo objects with same id have same hash
3. Todo objects can be used in sets for deduplication
4. Todo objects can be used as dict keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_hash_consistent_for_same_id() -> None:
    """hash(Todo) should return same value for todos with same id."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    # Both todos have same id, so they should have same hash
    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_for_different_id() -> None:
    """hash(Todo) should return different values for different ids."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy milk")

    # Different ids should generally produce different hashes
    # (not guaranteed but highly likely)
    assert hash(todo1) != hash(todo2)


def test_todo_in_set_works() -> None:
    """Todo objects should work in sets for deduplication."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="different text")  # Same id as todo1
    todo3 = Todo(id=2, text="another task")

    # Set should deduplicate based on id
    todo_set = {todo1, todo2, todo3}
    assert len(todo_set) == 2  # todo1 and todo2 are "same", todo3 is different


def test_todo_as_dict_key_works() -> None:
    """Todo objects should be usable as dict keys."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy bread")

    # Using todos as dict keys
    todo_dict = {todo1: "first", todo2: "second"}

    assert todo_dict[todo1] == "first"
    assert todo_dict[todo2] == "second"


def test_todo_dict_key_same_id_access() -> None:
    """Dict access should work with different Todo objects having same id."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="updated text")  # Same id as todo1

    todo_dict = {todo1: "value"}

    # Should be able to access using todo2 (same id as todo1)
    assert todo_dict[todo2] == "value"


def test_todo_hash_stable_across_field_changes() -> None:
    """Hash should be stable even if other fields change."""
    todo = Todo(id=1, text="original")
    original_hash = hash(todo)

    # Modify mutable fields (if Todo supported this)
    # The hash should still be based only on id
    todo2 = Todo(id=1, text="modified", done=True)

    # Same id should give same hash regardless of other fields
    assert hash(todo2) == original_hash
