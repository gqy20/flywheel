"""Tests for Todo.__eq__ and __hash__ methods (Issue #5986).

These tests verify that:
1. Todo objects can be compared for equality based on their content
2. Todo objects can be used in sets and as dict keys
3. Hash is based on id for consistent identity semantics
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_identical_todos_return_true() -> None:
    """Two Todos with same id, text, and done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2


def test_todo_eq_different_id_returns_false() -> None:
    """Todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_todo_eq_different_text_returns_false() -> None:
    """Todos with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2


def test_todo_eq_different_done_returns_false() -> None:
    """Todos with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2


def test_todo_eq_with_non_todo_returns_not_implemented() -> None:
    """Comparing Todo with non-Todo should return False."""
    todo = Todo(id=1, text="buy milk", done=False)

    # Todo should not be equal to non-Todo types
    assert todo != "buy milk"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk"}


def test_todo_can_be_added_to_set() -> None:
    """Todo objects should be hashable and usable in sets."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy bread", done=True)

    todo_set = {todo1, todo2}

    assert len(todo_set) == 2
    assert todo1 in todo_set
    assert todo2 in todo_set


def test_todo_set_deduplication() -> None:
    """Equal Todo objects should deduplicate in a set."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    todo_set = {todo1, todo2}

    # Two equal todos should result in a set of size 1
    assert len(todo_set) == 1


def test_todo_hash_based_on_id() -> None:
    """Todos with same id should have same hash regardless of other fields."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)

    # Same id should produce same hash
    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_id_different_hash() -> None:
    """Todos with different ids should have different hashes."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    # Different ids should likely produce different hashes
    # (not strictly guaranteed but expected behavior)
    assert hash(todo1) != hash(todo2)


def test_todo_can_be_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy bread", done=True)

    todo_dict = {todo1: "first", todo2: "second"}

    assert todo_dict[todo1] == "first"
    assert todo_dict[todo2] == "second"
