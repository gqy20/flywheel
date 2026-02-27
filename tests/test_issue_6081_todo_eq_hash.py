"""Tests for Todo.__eq__ and __hash__ methods (Issue #6081).

These tests verify that:
1. Two Todo objects with same id are equal regardless of other fields
2. Todo objects can be added to a set without errors
3. Todo objects can be used as dict keys
4. Hashing is based on id field only
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id_different_done_status() -> None:
    """Two Todo objects with same id should be equal regardless of done status."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_equality_same_id_different_text() -> None:
    """Two Todo objects with same id should be equal regardless of text."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=False)

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_equality_different_id() -> None:
    """Two Todo objects with different id should NOT be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2, "Todos with different id should not be equal"


def test_todo_hashable_in_set() -> None:
    """Todo objects should be hashable and usable in a set."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)
    todo3 = Todo(id=2, text="buy bread", done=False)

    # Should be able to add to a set
    todo_set = {todo1, todo2, todo3}

    # Set should deduplicate by id (todo1 and todo2 have same id)
    assert len(todo_set) == 2, f"Expected 2 unique todos, got {len(todo_set)}"


def test_todo_hash_consistent_after_modification() -> None:
    """Todo hash should be consistent after state changes."""
    todo = Todo(id=1, text="buy milk", done=False)
    original_hash = hash(todo)

    # Modify state
    todo.mark_done()
    assert hash(todo) == original_hash, "Hash should not change after mark_done()"

    # Modify text
    todo.rename("buy bread")
    assert hash(todo) == original_hash, "Hash should not change after rename()"


def test_todo_as_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)  # Same id, different state
    todo3 = Todo(id=2, text="buy bread", done=False)

    # Use todos as dict keys
    mapping = {todo1: "first", todo3: "third"}

    # todo2 should map to same key as todo1 (same id)
    assert mapping[todo2] == "first", "Todos with same id should map to same dict entry"


def test_todo_equality_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != 1, "Todo should not equal an int"
    assert todo != "buy milk", "Todo should not equal a string"
    assert todo != {"id": 1, "text": "buy milk"}, "Todo should not equal a dict"


def test_todo_hash_after_timestamp_update() -> None:
    """Todo hash should remain stable even after timestamp updates."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    # Even with different timestamps, they should hash the same
    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"

    # After mark_done updates the timestamp, hash should still be same
    todo1.mark_done()
    assert hash(todo1) == hash(todo2), "Hash should be based on id, not timestamp"
