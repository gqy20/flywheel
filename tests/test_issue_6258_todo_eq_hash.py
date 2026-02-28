"""Tests for Todo.__eq__ and __hash__ methods (Issue #6258).

These tests verify that:
1. Todo objects with same id are equal regardless of other fields
2. Todo objects with different ids are not equal
3. Todo objects can be used in sets for deduplication
4. Todo objects can be hashed and used as dict keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_different_text() -> None:
    """Todo objects with same id should be equal regardless of text."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_eq_same_id_different_done() -> None:
    """Todo objects with same id should be equal regardless of done status."""
    todo1 = Todo(id=1, text="task", done=False)
    todo2 = Todo(id=1, text="task", done=True)

    assert todo1 == todo2, "Todos with same id should be equal even with different done"


def test_todo_neq_different_id() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text")
    todo2 = Todo(id=2, text="same text")

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_eq_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="task")

    assert todo != 1, "Todo should not equal an integer"
    assert todo != "task", "Todo should not equal a string"
    assert todo != {"id": 1, "text": "task"}, "Todo should not equal a dict"


def test_todo_hash_same_id() -> None:
    """Todo objects with same id should have same hash."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")

    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_hash_different_id() -> None:
    """Todo objects with different ids should have different hashes."""
    todo1 = Todo(id=1, text="same text")
    todo2 = Todo(id=2, text="same text")

    # Different ids should typically produce different hashes
    # (not guaranteed but expected for distinct integers)
    assert hash(todo1) != hash(todo2), "Todos with different ids should have different hashes"


def test_todo_in_set() -> None:
    """Todo objects should be usable in a set."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task two")
    todo3 = Todo(id=1, text="task one duplicate")  # Same id as todo1

    todo_set = {todo1, todo2, todo3}

    # Set should deduplicate based on id
    assert len(todo_set) == 2, f"Set should have 2 unique todos, got {len(todo_set)}"


def test_todo_as_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="original")
    todo2 = Todo(id=1, text="updated")  # Same id as todo1

    d = {todo1: "value1"}

    # Should be able to access using todo2 since it has same id
    assert d[todo2] == "value1", "Should access dict using Todo with same id"


def test_todo_set_deduplication() -> None:
    """Multiple Todo objects with same id in a set should be deduplicated."""
    todos = [
        Todo(id=1, text="first"),
        Todo(id=1, text="second"),
        Todo(id=1, text="third"),
        Todo(id=2, text="other"),
    ]

    unique_todos = set(todos)

    assert len(unique_todos) == 2, f"Expected 2 unique todos, got {len(unique_todos)}"


def test_todo_hash_consistency() -> None:
    """Hash should be consistent across multiple calls."""
    todo = Todo(id=42, text="test task")

    hash1 = hash(todo)
    hash2 = hash(todo)
    hash3 = hash(todo)

    assert hash1 == hash2 == hash3, "Hash should be consistent"
