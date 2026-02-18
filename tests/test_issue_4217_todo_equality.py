"""Tests for Todo.__eq__ and __hash__ methods (Issue #4217).

These tests verify that:
1. Todo objects with same business fields (id, text, done) are equal
2. Timestamps (created_at, updated_at) are not part of equality
3. Todo objects can be used in sets via __hash__
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_business_fields() -> None:
    """Todo objects with same id, text, done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00Z", updated_at="2024-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-12-31T23:59:59Z", updated_at="2024-12-31T23:59:59Z")

    # Should be equal despite different timestamps
    assert todo1 == todo2


def test_todo_equality_different_id() -> None:
    """Todo objects with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_todo_equality_different_text() -> None:
    """Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2


def test_todo_equality_different_done() -> None:
    """Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2


def test_todo_hash_for_set_operations() -> None:
    """Todo objects should be hashable and usable in sets."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-12-31T23:59:59Z")
    todo3 = Todo(id=2, text="buy bread", done=False)

    # Equal todos should have same hash
    assert hash(todo1) == hash(todo2)

    # Should be usable in a set (deduplication)
    todo_set = {todo1, todo2, todo3}
    assert len(todo_set) == 2  # todo1 and todo2 are same, todo3 is different


def test_todo_hash_different_id() -> None:
    """Todo objects with different id should have different hashes."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    # Different ids should have different hashes
    assert hash(todo1) != hash(todo2)


def test_todo_equality_reflexive() -> None:
    """A Todo should equal itself."""
    todo = Todo(id=1, text="buy milk", done=False)
    assert todo == todo


def test_todo_equality_symmetric() -> None:
    """If todo1 == todo2, then todo2 == todo1."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_equality_transitive() -> None:
    """If todo1 == todo2 and todo2 == todo3, then todo1 == todo3."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    todo3 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3


def test_todo_not_equal_to_non_todo() -> None:
    """A Todo should not be equal to a non-Todo object."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk", "done": False}
    assert todo != None
