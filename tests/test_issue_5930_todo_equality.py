"""Tests for Todo.__eq__ and __hash__ methods (Issue #5930).

These tests verify that:
1. Todo equality is based solely on id (not other fields)
2. Todo hashing is consistent with equality (same id = same hash)
3. Todo objects can be used in sets and as dict keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_based_on_id_only() -> None:
    """Todos with the same id should be equal regardless of other fields."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    assert todo1 == todo2


def test_todo_inequality_different_id() -> None:
    """Todos with different ids should not be equal even with same other fields."""
    todo1 = Todo(id=1, text="same text", done=False)
    todo2 = Todo(id=2, text="same text", done=False)

    assert todo1 != todo2


def test_todo_hash_based_on_id() -> None:
    """Todos with the same id should have the same hash."""
    todo1 = Todo(id=1, text="text one")
    todo2 = Todo(id=1, text="text two")

    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_id() -> None:
    """Todos with different ids should (usually) have different hashes."""
    todo1 = Todo(id=1, text="same text")
    todo2 = Todo(id=2, text="same text")

    # Hash collisions are possible but unlikely for sequential ids
    assert hash(todo1) != hash(todo2)


def test_todo_set_deduplication() -> None:
    """Todos with same id should be deduplicated in sets."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")
    todo3 = Todo(id=2, text="third")

    todo_set = {todo1, todo2, todo3}

    # Should only have 2 unique todos (id=1 and id=2)
    assert len(todo_set) == 2


def test_todo_dict_key_usage() -> None:
    """Todos with same id should be treated as same dict key."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")

    todo_dict = {todo1: "value1"}
    todo_dict[todo2] = "value2"

    # Should only have 1 entry since todo1 and todo2 have same id
    assert len(todo_dict) == 1
    assert todo_dict[todo1] == "value2"


def test_todo_equality_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="task")

    assert todo != 1
    assert todo != "1"
    assert todo != {"id": 1, "text": "task"}
    assert todo != None  # noqa: E711
