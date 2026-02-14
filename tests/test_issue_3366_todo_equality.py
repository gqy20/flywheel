"""Tests for Todo equality comparison support (Issue #3366).

These tests verify that:
1. Todo objects with same id, text, and done compare as equal
2. Todo objects with different id/text/done compare as not equal
3. Todo objects can be used in sets (hashable via id field)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_values() -> None:
    """Todos with same id, text, and done should be equal."""
    # Use fixed timestamps to avoid timing issues in comparison
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    assert todo1 == todo2


def test_todo_equality_different_id() -> None:
    """Todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)
    assert todo1 != todo2


def test_todo_equality_different_text() -> None:
    """Todos with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)
    assert todo1 != todo2


def test_todo_equality_different_done() -> None:
    """Todos with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)
    assert todo1 != todo2


def test_todo_set_deduplication() -> None:
    """Todo objects should be usable in sets for deduplication."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    todo3 = Todo(id=2, text="buy bread", done=False)

    # Set should deduplicate identical todos and keep distinct ones
    todo_set = {todo1, todo2, todo3}
    assert len(todo_set) == 2


def test_todo_hash_consistency() -> None:
    """Equal Todo objects should have same hash."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    assert hash(todo1) == hash(todo2)
