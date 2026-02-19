"""Tests for Todo.__eq__ and __hash__ methods (Issue #4550).

These tests verify that:
1. Todo equality compares identity fields (id, text, done)
2. Todos with same id have same hash (stable hashing)
3. Todos can be used in sets and dict keys
4. Timestamps don't affect equality or hashing
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_values() -> None:
    """Two todos with same id, text, done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2


def test_todo_equality_different_id() -> None:
    """Todos with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_todo_equality_different_text() -> None:
    """Todos with same id but different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2


def test_todo_equality_different_done() -> None:
    """Todos with same id but different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2


def test_todo_hash_based_on_id() -> None:
    """Hash should be based on id for stable hashing."""
    # Todos with same id should have same hash (even if other fields differ)
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)

    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_ids() -> None:
    """Todos with different id should have different hash."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert hash(todo1) != hash(todo2)


def test_todo_in_set() -> None:
    """Todos can be used in a set."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)  # Same identity fields
    todo3 = Todo(id=2, text="buy bread", done=False)

    todo_set = {todo1, todo2, todo3}

    # Only 2 distinct todos (1 and 2)
    assert len(todo_set) == 2


def test_todo_as_dict_key() -> None:
    """Todos can be used as dictionary keys."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)  # Same identity fields

    d = {todo1: "value1"}
    d[todo2] = "value2"  # Should overwrite value1

    assert len(d) == 1
    assert d[todo1] == "value2"


def test_todo_equality_ignores_timestamps() -> None:
    """Equality should ignore timestamps."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    # Modify timestamps to be different
    todo1.updated_at = "2024-01-01T00:00:00+00:00"
    todo2.updated_at = "2025-12-31T23:59:59+00:00"

    # Should still be equal because id, text, done are the same
    assert todo1 == todo2
