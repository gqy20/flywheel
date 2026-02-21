"""Tests for Todo.__eq__ and __hash__ methods (Issue #4550).

These tests verify that:
1. Todo objects have proper equality comparison based on id, text, done
2. Todo objects are hashable and can be used in sets/dicts
3. Hash is based on id for stable hashing
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_values() -> None:
    """Two todos with same id, text, done should be equal."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=False)
    assert todo1 == todo2


def test_todo_equality_different_id() -> None:
    """Two todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=2, text="a", done=False)
    assert todo1 != todo2


def test_todo_equality_different_text() -> None:
    """Two todos with different text should not be equal."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="b", done=False)
    assert todo1 != todo2


def test_todo_equality_different_done() -> None:
    """Two todos with different done status should not be equal."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=True)
    assert todo1 != todo2


def test_todo_equality_ignores_timestamps() -> None:
    """Two todos with same id, text, done but different timestamps should be equal."""
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="a", done=False, created_at="2025-12-31T23:59:59+00:00", updated_at="2025-12-31T23:59:59+00:00")
    assert todo1 == todo2


def test_todo_hash_based_on_id() -> None:
    """Hash should be based on id for stable hashing."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="b", done=True)  # Different text and done
    # Same id should produce same hash
    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_ids() -> None:
    """Different ids should produce different hashes."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=2, text="a", done=False)
    # Different ids should produce different hashes (not guaranteed but expected)
    assert hash(todo1) != hash(todo2)


def test_todo_usable_in_set() -> None:
    """Todos should be usable in a set."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=False)  # Same identity
    todo3 = Todo(id=2, text="a", done=False)  # Different id

    # Set with duplicate (by equality) should have size 1
    todo_set = {todo1, todo2}
    assert len(todo_set) == 1

    # Set with different todos should have size 2
    todo_set = {todo1, todo3}
    assert len(todo_set) == 2


def test_todo_usable_as_dict_key() -> None:
    """Todos should be usable as dict keys."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=False)  # Same identity

    d = {todo1: "value1"}
    # Same todo should map to same value
    assert d[todo2] == "value1"


def test_todo_equality_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="a", done=False)
    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "a", "done": False}
