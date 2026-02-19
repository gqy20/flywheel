"""Tests for Todo hash support (Issue #4441).

These tests verify that:
1. Todo objects are hashable based on their id
2. Todos with the same id have the same hash
3. Todo objects can be used in sets for deduplication
4. Todo objects can be used as dictionary keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_hash_consistent_for_same_id() -> None:
    """hash(Todo) should return the same value for todos with the same id."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="different text")
    todo3 = Todo(id=2, text="buy milk")

    # Same id should have same hash regardless of other fields
    assert hash(todo1) == hash(todo2)
    # Different id should have different hash
    assert hash(todo1) != hash(todo3)


def test_todo_hash_stable() -> None:
    """hash(Todo) should be stable across multiple calls."""
    todo = Todo(id=42, text="stable hash test")

    hash1 = hash(todo)
    hash2 = hash(todo)
    hash3 = hash(todo)

    assert hash1 == hash2 == hash3


def test_todo_in_set_works() -> None:
    """Todo objects should work in sets for deduplication."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")  # Same id, different text
    todo3 = Todo(id=2, text="third")

    todo_set = {todo1, todo2, todo3}

    # Only 2 items because todo1 and todo2 have the same id
    assert len(todo_set) == 2


def test_todo_set_deduplication() -> None:
    """Set should deduplicate todos with the same id."""
    todos = [
        Todo(id=1, text="first"),
        Todo(id=1, text="second"),
        Todo(id=1, text="third"),
        Todo(id=2, text="fourth"),
        Todo(id=2, text="fifth"),
    ]

    unique_ids = {t.id for t in todos}
    assert unique_ids == {1, 2}


def test_todo_as_dict_key_works() -> None:
    """Todo objects should work as dictionary keys."""
    todo1 = Todo(id=1, text="key one")
    todo2 = Todo(id=2, text="key two")

    # Use todos as dict keys
    todo_dict = {
        todo1: "value one",
        todo2: "value two",
    }

    assert todo_dict[todo1] == "value one"
    assert todo_dict[todo2] == "value two"


def test_todo_dict_key_lookup_by_same_id() -> None:
    """Dict lookup should work with a different Todo object having same id."""
    original = Todo(id=1, text="original")
    lookup = Todo(id=1, text="lookup key")

    todo_dict = {original: "stored value"}

    # Should be able to look up using a different instance with same id
    # This requires __hash__ AND __eq__ to be consistent
    assert todo_dict.get(lookup) == "stored value"


def test_todo_hash_after_state_change() -> None:
    """Todo hash should remain stable even if mutable fields change."""
    todo = Todo(id=1, text="original text")
    original_hash = hash(todo)

    # Mutate the todo
    todo.mark_done()

    # Hash should still be the same (based on id, not mutable state)
    assert hash(todo) == original_hash
