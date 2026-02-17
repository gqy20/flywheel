"""Tests for Todo equality and hash based on id (Issue #3897).

These tests verify that:
1. Todo equality is based on id field only
2. Todo can be hashed using id
3. Todos can be used in sets for deduplication
4. Todos with same id but different other fields are equal
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id_different_text() -> None:
    """Todos with same id should be equal regardless of text."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_equality_same_id_different_done() -> None:
    """Todos with same id should be equal regardless of done status."""
    todo1 = Todo(id=1, text="task", done=False)
    todo2 = Todo(id=1, text="task", done=True)

    assert todo1 == todo2, "Todos with same id should be equal even if done differs"


def test_todo_inequality_different_id() -> None:
    """Todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text")
    todo2 = Todo(id=2, text="same text")

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_hash_based_on_id() -> None:
    """Todo should be hashable based on id."""
    todo = Todo(id=1, text="task")

    # Should not raise TypeError
    hash_value = hash(todo)

    # Hash should be based on id
    assert hash_value == hash(1)


def test_todo_hash_consistent() -> None:
    """Todo hash should be consistent for same id."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=1, text="task two")

    # Same id should produce same hash
    assert hash(todo1) == hash(todo2)


def test_todo_set_deduplication() -> None:
    """Todos with same id should be deduplicated in sets."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")
    todo3 = Todo(id=2, text="third")

    todo_set = {todo1, todo2, todo3}

    # Should only have 2 unique todos (id=1 and id=2)
    assert len(todo_set) == 2, f"Expected 2 unique todos, got {len(todo_set)}"


def test_todo_dict_key() -> None:
    """Todos should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")

    d = {todo1: "value1"}

    # Same id should map to same key
    assert d[todo2] == "value1"


def test_todo_equality_with_non_todo() -> None:
    """Todo equality with non-Todo should return False."""
    todo = Todo(id=1, text="task")

    # Should not be equal to non-Todo objects
    assert todo != 1
    assert todo != "1"
    assert todo != {"id": 1, "text": "task"}
    assert todo != object()
