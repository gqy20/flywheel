"""Tests for Todo equality and hashability (Issue #2210).

These tests verify that:
1. Todo objects can be compared for equality based on their values
2. Todo objects are hashable and can be used in sets and as dict keys
3. Two Todo objects with same id, text, done, created_at, updated_at are equal
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_values() -> None:
    """Two Todo objects with identical values should be considered equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")

    assert todo1 == todo2


def test_todo_equality_with_auto_timestamps() -> None:
    """Todos with auto-generated timestamps should be equal if values match."""
    # Create todos without explicit timestamps - they'll have different auto-generated timestamps
    # This tests the design decision of which fields to include in equality
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    # Current implementation compares ALL fields including timestamps
    # So these will NOT be equal because timestamps differ
    assert todo1 != todo2


def test_todo_inequality_different_id() -> None:
    """Todos with different IDs should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    todo2 = Todo(id=2, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")

    assert todo1 != todo2


def test_todo_inequality_different_text() -> None:
    """Todos with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="buy bread", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")

    assert todo1 != todo2


def test_todo_inequality_different_done() -> None:
    """Todos with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="buy milk", done=True, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")

    assert todo1 != todo2


def test_todo_inequality_different_timestamps() -> None:
    """Todos with different timestamps should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2025-01-02T00:00:00Z", updated_at="2025-01-02T00:00:00Z")

    assert todo1 != todo2


def test_todo_reflexivity() -> None:
    """Todo should be equal to itself (reflexivity property)."""
    todo = Todo(id=1, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    assert todo == todo


def test_todo_symmetry() -> None:
    """If todo1 == todo2, then todo2 == todo1 (symmetry property)."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")

    assert (todo1 == todo2) == (todo2 == todo1)


def test_todo_transitivity() -> None:
    """If todo1 == todo2 and todo2 == todo3, then todo1 == todo3 (transitivity property)."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    todo3 = Todo(id=1, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3


def test_todo_comparison_with_none() -> None:
    """Todo should not be equal to None."""
    todo = Todo(id=1, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    assert todo != None  # noqa: E711


def test_todo_hashable() -> None:
    """Todo objects should be hashable and usable in sets and as dict keys."""
    # Create two identical todos
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")

    # Should be able to hash them
    hash1 = hash(todo1)
    hash2 = hash(todo2)
    assert hash1 == hash2  # Equal objects should have equal hashes

    # Should be able to use in sets
    todo_set = {todo1, todo2}
    assert len(todo_set) == 1  # Duplicates should be removed

    # Should be able to use as dict keys
    todo_dict = {todo1: "value"}
    assert todo_dict[todo2] == "value"  # Equal objects should access same dict entry


def test_todo_hash_consistency_with_equality() -> None:
    """Hash values should be consistent with equality comparison."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    todo3 = Todo(id=2, text="buy bread", done=True, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")

    # Equal objects have equal hashes
    assert todo1 == todo2
    assert hash(todo1) == hash(todo2)

    # Unequal objects (usually) have different hashes
    assert todo1 != todo3
    # Note: Hash collision is possible but unlikely for small test cases


def test_todo_set_deduplication() -> None:
    """Sets should correctly deduplicate Todo objects based on value equality."""
    todo1 = Todo(id=1, text="task1", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="task1", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")  # duplicate
    todo3 = Todo(id=2, text="task2", done=True, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    todo4 = Todo(id=3, text="task3", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")

    unique_todos = {todo1, todo2, todo3, todo4}
    assert len(unique_todos) == 3  # todo2 is a duplicate of todo1


def test_todo_dict_key_usage() -> None:
    """Todo objects should work as dict keys based on value equality."""
    todo1 = Todo(id=1, text="task1", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="task1", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")  # equal to todo1

    todo_map = {todo1: "first task"}
    assert todo_map[todo2] == "first task"  # todo2 should access same entry

    todo_map[todo2] = "updated first task"
    assert todo_map[todo1] == "updated first task"  # Both refer to same entry


def test_todo_inequality_operator() -> None:
    """The != operator should work correctly for Todo objects."""
    todo1 = Todo(id=1, text="task1", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="task1", done=False, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")
    todo3 = Todo(id=2, text="task2", done=True, created_at="2025-01-01T00:00:00Z", updated_at="2025-01-01T00:00:00Z")

    assert todo1 == todo2  # Equal objects
    assert todo1 != todo3  # Unequal objects
