"""Tests for Todo.__eq__ and __hash__ methods (Issue #3100).

These tests verify that:
1. Todo objects with the same id compare equal regardless of other fields
2. Todo objects are hashable and can be used in sets/dicts
3. Equality is based on id as the unique identifier
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_based_on_id() -> None:
    """Two Todo objects with same id should compare equal regardless of other fields."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_inequality_different_ids() -> None:
    """Two Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_hash_consistency() -> None:
    """Hash of Todo objects with same id should be equal."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")

    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_hashable_for_set() -> None:
    """Todo objects should be usable in sets."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task two")
    todo3 = Todo(id=1, text="duplicate of task one")

    todo_set = {todo1, todo2, todo3}

    # Should deduplicate to 2 items since todo1 and todo3 have same id
    assert len(todo_set) == 2, f"Set should have 2 unique todos, got {len(todo_set)}"


def test_todo_hashable_for_dict_key() -> None:
    """Todo objects should be usable as dict keys."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task two")

    todo_dict = {todo1: "first", todo2: "second"}

    # Looking up with a different Todo object with same id should find the key
    todo1_copy = Todo(id=1, text="different text")
    assert todo_dict[todo1_copy] == "first", "Should find dict entry by id equality"


def test_todo_not_equal_to_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="task")

    assert todo != 1, "Todo should not equal integer"
    assert todo != "task", "Todo should not equal string"
    assert todo != {"id": 1}, "Todo should not equal dict"
    assert todo is not None, "Todo should not equal None"


def test_todo_hash_stable_across_field_changes() -> None:
    """Todo hash should remain stable when other fields change (id is the key)."""
    todo = Todo(id=1, text="original")
    original_hash = hash(todo)

    # Modify text
    todo.rename("modified")
    assert hash(todo) == original_hash, "Hash should not change when text changes"

    # Modify done status
    todo.mark_done()
    assert hash(todo) == original_hash, "Hash should not change when done changes"
