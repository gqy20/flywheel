"""Tests for Todo __eq__ and __hash__ methods (Issue #7262).

These tests verify that:
1. Todo objects are compared by id (not by object identity)
2. Todo objects can be hashed consistently by id
3. Todo objects can be used in sets for deduplication
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_by_id() -> None:
    """Todo objects with the same id should be equal, regardless of other fields."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="b", done=True)

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_inequality_by_different_id() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=2, text="a", done=False)

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_hash_consistent() -> None:
    """Todo objects with the same id should have the same hash."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="b", done=True)

    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_in_set() -> None:
    """Todo objects should work in sets and deduplicate by id."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")  # Same id, different text
    todo3 = Todo(id=2, text="third")

    todo_set = {todo1, todo2, todo3}

    # Should have only 2 elements (todo1 and todo2 have same id)
    assert len(todo_set) == 2, f"Expected 2 unique todos, got {len(todo_set)}"


def test_todo_hash_different_for_different_ids() -> None:
    """Todo objects with different ids should (likely) have different hashes."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")

    # While hash collisions are theoretically possible, for small integers they shouldn't happen
    assert hash(todo1) != hash(todo2), "Todos with different ids should have different hashes"


def test_todo_equality_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="task")

    assert todo != 1, "Todo should not equal an integer"
    assert todo != "1", "Todo should not equal a string"
    assert todo != {"id": 1, "text": "task"}, "Todo should not equal a dict"
    assert todo != object(), "Todo should not equal an arbitrary object"


def test_todo_set_operations() -> None:
    """Todo objects should support common set operations."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task two")
    todo3 = Todo(id=1, text="task one updated")  # Same id as todo1

    set_a = {todo1, todo2}
    set_b = {todo2, todo3}

    # Union should have 2 unique todos (ids 1 and 2)
    union = set_a | set_b
    assert len(union) == 2

    # Intersection should have 2 todos (id 1 and id 2 are in both sets)
    # Note: todo3 has same id as todo1, so id=1 is in both sets
    intersection = set_a & set_b
    assert len(intersection) == 2

    # Difference: set_a - set_b should be empty (both id 1 and id 2 are in both sets)
    difference = set_a - set_b
    assert len(difference) == 0


def test_todo_hash_stable() -> None:
    """Todo hash should be stable across multiple calls."""
    todo = Todo(id=42, text="stable hash test")

    hash1 = hash(todo)
    hash2 = hash(todo)
    hash3 = hash(todo)

    assert hash1 == hash2 == hash3, "Hash should be stable across calls"
