"""Tests for Todo equality and hashing (Issue #2210).

These tests verify that:
1. Todo objects with same values are considered equal
2. Todo objects with different values are not equal
3. Todo objects can be used in sets and as dict keys (hashable)
4. __eq__ compares all relevant fields (id, text, done, created_at, updated_at)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_values() -> None:
    """Two Todo objects with same id, text, done, timestamps should be equal."""
    # Use explicit timestamps to ensure equality works as expected
    # (without explicit timestamps, __post_init__ would generate different ones)
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01", updated_at="2024-01-01")

    assert todo1 == todo2


def test_todo_equality_with_timestamps() -> None:
    """Two Todo objects with same values including timestamps should be equal."""
    todo1 = Todo(id=1, text="task", done=True, created_at="2024-01-01", updated_at="2024-01-02")
    todo2 = Todo(id=1, text="task", done=True, created_at="2024-01-01", updated_at="2024-01-02")

    assert todo1 == todo2


def test_todo_inequality_different_id() -> None:
    """Todo objects with different id should not be equal."""
    todo1 = Todo(id=1, text="same text", done=False)
    todo2 = Todo(id=2, text="same text", done=False)

    assert todo1 != todo2


def test_todo_inequality_different_text() -> None:
    """Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="text a", done=False)
    todo2 = Todo(id=1, text="text b", done=False)

    assert todo1 != todo2


def test_todo_inequality_different_done() -> None:
    """Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="task", done=False)
    todo2 = Todo(id=1, text="task", done=True)

    assert todo1 != todo2


def test_todo_inequality_different_timestamps() -> None:
    """Todo objects with different timestamps should not be equal."""
    todo1 = Todo(id=1, text="task", done=False, created_at="2024-01-01", updated_at="2024-01-02")
    todo2 = Todo(id=1, text="task", done=False, created_at="2024-01-03", updated_at="2024-01-04")

    assert todo1 != todo2


def test_todo_hashable() -> None:
    """Todo objects should be hashable and usable in sets."""
    # Use explicit timestamps so todo1 and todo2 are equal
    todo1 = Todo(id=1, text="task a", created_at="2024-01-01", updated_at="2024-01-01")
    todo2 = Todo(id=1, text="task a", created_at="2024-01-01", updated_at="2024-01-01")
    todo3 = Todo(id=2, text="task b", created_at="2024-01-01", updated_at="2024-01-01")

    # Should be able to create a set of todos
    todo_set = {todo1, todo2, todo3}

    # Set should contain only 2 unique items (todo1 and todo2 are equal)
    assert len(todo_set) == 2


def test_todo_hash_consistent_with_equality() -> None:
    """Hash should be consistent with equality - equal objects have same hash."""
    # Use explicit timestamps for consistent hashing
    todo1 = Todo(id=1, text="task", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    todo2 = Todo(id=1, text="task", done=False, created_at="2024-01-01", updated_at="2024-01-01")

    # Equal objects should have the same hash
    assert hash(todo1) == hash(todo2)


def test_todo_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    # Use explicit timestamps so todo1 and todo2 are equal
    todo1 = Todo(id=1, text="task a", created_at="2024-01-01", updated_at="2024-01-01")
    todo2 = Todo(id=1, text="task a", created_at="2024-01-01", updated_at="2024-01-01")  # Equal to todo1
    todo3 = Todo(id=2, text="task b", created_at="2024-01-01", updated_at="2024-01-01")

    todo_dict = {todo1: "first", todo3: "second"}

    # todo2 should map to same value as todo1 since they're equal
    assert todo_dict[todo2] == "first"
    assert todo_dict[todo3] == "second"
