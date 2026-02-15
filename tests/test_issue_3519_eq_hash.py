"""Tests for Todo.__eq__ and __hash__ methods (Issue #3519).

These tests verify that:
1. Todo objects with same id are equal (regardless of other fields)
2. Todo objects can be hashed
3. Todo objects can be added to sets and deduplicated by id
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_equal() -> None:
    """Todo objects with same id should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_eq_different_id_not_equal() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text", done=True)
    todo2 = Todo(id=2, text="same text", done=True)

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_eq_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="task")
    assert todo != 1
    assert todo != "1"
    assert todo != {"id": 1, "text": "task"}
    assert todo is not None


def test_todo_hash_consistent() -> None:
    """hash(Todo) should be consistent based on id."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=1, text="task two")

    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_hash_different_ids() -> None:
    """hash(Todo) should differ for different ids."""
    todo1 = Todo(id=1, text="task")
    todo2 = Todo(id=2, text="task")

    assert hash(todo1) != hash(todo2), "Todos with different ids should have different hashes"


def test_todo_can_be_added_to_set() -> None:
    """Todo objects should be addable to a set."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task two")
    todo3 = Todo(id=1, text="task three")  # Same id as todo1

    todo_set = {todo1, todo2, todo3}

    # Set should have 2 items (todo1 and todo2, with todo3 being deduplicated)
    assert len(todo_set) == 2, f"Expected 2 items in set, got {len(todo_set)}"


def test_todo_set_deduplication_by_id() -> None:
    """Todo objects should be deduplicated by id in sets."""
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=1, text="duplicate of first"),
        Todo(id=3, text="third"),
        Todo(id=2, text="duplicate of second"),
    ]

    unique_todos = set(todos)

    # Should have 3 unique todos (by id)
    assert len(unique_todos) == 3, f"Expected 3 unique todos, got {len(unique_todos)}"


def test_todo_eq_reflexive() -> None:
    """Todo should be equal to itself."""
    todo = Todo(id=1, text="task")
    assert todo == todo


def test_todo_eq_symmetric() -> None:
    """Todo equality should be symmetric (a == b implies b == a)."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=1, text="task two")

    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_eq_transitive() -> None:
    """Todo equality should be transitive."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=1, text="task two")
    todo3 = Todo(id=1, text="task three")

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3
