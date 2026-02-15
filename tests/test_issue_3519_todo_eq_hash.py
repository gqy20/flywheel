"""Tests for Todo.__eq__ and __hash__ methods (Issue #3519).

These tests verify that:
1. Todo objects with same id are equal regardless of other fields
2. Todo objects can be hashed and used in sets
3. Todo objects with different ids are not equal
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_equal() -> None:
    """Todo objects with same id should be equal regardless of other fields."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy eggs", done=True)

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_eq_different_id_not_equal() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_eq_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="buy milk")

    assert todo != 1, "Todo should not equal an integer with same value as id"
    assert todo != "1", "Todo should not equal a string"
    assert todo != {"id": 1}, "Todo should not equal a dict"
    assert todo is not None, "Todo should not equal None"


def test_todo_hash_consistent() -> None:
    """hash(Todo) should be consistent for same id."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy eggs")

    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_hash_different_for_different_id() -> None:
    """hash(Todo) should likely be different for different ids."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy milk")

    # While hash collisions are possible, for sequential ints they should differ
    assert hash(todo1) != hash(todo2), "Todos with different ids should have different hashes"


def test_todo_can_be_added_to_set() -> None:
    """Todo objects should be hashable and usable in sets."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy eggs")  # Same id
    todo3 = Todo(id=2, text="buy bread")

    todo_set = {todo1, todo2, todo3}

    # Set should deduplicate based on hash/eq (same id = same element)
    assert len(todo_set) == 2, f"Set should have 2 unique todos, got {len(todo_set)}"
    assert todo1 in todo_set
    assert todo2 in todo_set  # Same as todo1
    assert todo3 in todo_set


def test_todo_set_deduplication_by_id() -> None:
    """Set should deduplicate Todo objects by id."""
    todos = [
        Todo(id=1, text="task a"),
        Todo(id=1, text="task b"),  # Duplicate id
        Todo(id=2, text="task c"),
        Todo(id=2, text="task d"),  # Duplicate id
        Todo(id=3, text="task e"),
    ]

    unique_todos = set(todos)

    assert len(unique_todos) == 3, f"Should have 3 unique todos by id, got {len(unique_todos)}"


def test_todo_hash_stable_across_calls() -> None:
    """Hash should be stable across multiple calls."""
    todo = Todo(id=42, text="stable hash test")

    hash1 = hash(todo)
    hash2 = hash(todo)
    hash3 = hash(todo)

    assert hash1 == hash2 == hash3, "Hash should be stable"


def test_todo_eq_reflexive() -> None:
    """A Todo should equal itself."""
    todo = Todo(id=1, text="reflexive test")

    assert todo == todo, "Todo should equal itself"


def test_todo_eq_symmetric() -> None:
    """Equality should be symmetric (a == b implies b == a)."""
    todo1 = Todo(id=1, text="symmetric test 1")
    todo2 = Todo(id=1, text="symmetric test 2")

    assert todo1 == todo2
    assert todo2 == todo1, "Equality should be symmetric"


def test_todo_eq_transitive() -> None:
    """Equality should be transitive (a == b and b == c implies a == c)."""
    todo1 = Todo(id=1, text="transitive test 1")
    todo2 = Todo(id=1, text="transitive test 2")
    todo3 = Todo(id=1, text="transitive test 3")

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3, "Equality should be transitive"
