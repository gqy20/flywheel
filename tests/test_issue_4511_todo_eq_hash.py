"""Tests for Todo.__eq__ and __hash__ methods (Issue #4511).

These tests verify that:
1. Todo objects with the same id are equal (__eq__)
2. Todo objects with different ids are not equal (__eq__)
3. Todo objects can be hashed based on id (__hash__)
4. Todo objects can be used in sets for deduplication
5. Todo objects can be used as dictionary keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id() -> None:
    """Todo(id=1, text='a') == Todo(id=1, text='a') should return True."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    assert todo1 == todo2, "Todos with same id and same fields should be equal"


def test_todo_eq_same_id_different_fields() -> None:
    """Todos with same id but different other fields should be equal.

    The 'id' field is the unique identifier, so equality is based on id only.
    """
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)
    assert todo1 == todo2, "Todos with same id should be equal regardless of other fields"


def test_todo_neq_different_id() -> None:
    """Todo(id=1) != Todo(id=2) should return True."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)
    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_hash_consistent() -> None:
    """hash(Todo) should return consistent value for same id."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)

    # Same id should produce same hash
    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"

    # Hash should be consistent across multiple calls
    assert hash(todo1) == hash(todo1), "Hash should be consistent across calls"


def test_todo_hash_different() -> None:
    """hash(Todo) should return different values for different ids."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy milk")

    # Different ids should produce different hashes (with high probability)
    assert hash(todo1) != hash(todo2), "Todos with different ids should have different hashes"


def test_todo_in_set() -> None:
    """Todo objects can be added to a set and deduplicated by id."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)  # Same id as todo1
    todo3 = Todo(id=2, text="buy bread", done=False)

    todo_set = {todo1, todo2, todo3}

    # Set should have 2 unique items (todo1 and todo2 are same id)
    assert len(todo_set) == 2, f"Set should have 2 unique todos, got {len(todo_set)}"
    assert todo1 in todo_set
    assert todo3 in todo_set


def test_todo_as_dict_key() -> None:
    """Todo objects can be used as dictionary keys."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)  # Same id as todo1
    todo3 = Todo(id=2, text="clean house", done=False)

    # Using todos as dict keys
    todo_dict = {todo1: "value1", todo3: "value2"}

    # todo2 should map to same key as todo1 (same id)
    assert todo_dict[todo2] == "value1", "Todo with same id should map to same dict entry"

    # todo3 should have its own entry
    assert todo_dict[todo3] == "value2"


def test_todo_eq_with_non_todo() -> None:
    """Todo.__eq__ should return NotImplemented for non-Todo objects."""
    todo = Todo(id=1, text="buy milk", done=False)

    # Comparing with non-Todo should return False (NotImplemented falls back to identity)
    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk"}


def test_todo_hash_based_on_id() -> None:
    """Verify that hash is based on id field."""
    todo = Todo(id=42, text="test", done=True)

    # Hash should be the same as hashing the id directly
    assert hash(todo) == hash(42), "Todo hash should be based on id field"
