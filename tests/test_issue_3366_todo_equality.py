"""Tests for Todo equality comparison support (Issue #3366).

These tests verify that:
1. Todo objects with same id/text/done compare as equal
2. Todo objects with different fields compare as not equal
3. Todo objects can be hashed by id for use in sets
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_values() -> None:
    """Todos with same id, text, and done should be equal."""
    # We compare only id, text, done (timestamps are auto-generated)
    # For equality to work, we need to fix the timestamps too
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="a", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    assert todo1 == todo2, "Todos with same values should be equal"


def test_todo_equality_different_id() -> None:
    """Todos with different id should not be equal."""
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=2, text="a", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    assert todo1 != todo2, "Todos with different id should not be equal"


def test_todo_equality_different_text() -> None:
    """Todos with different text should not be equal."""
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="b", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    assert todo1 != todo2, "Todos with different text should not be equal"


def test_todo_equality_different_done() -> None:
    """Todos with different done status should not be equal."""
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="a", done=True, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    assert todo1 != todo2, "Todos with different done status should not be equal"


def test_todo_hashable_by_id() -> None:
    """Todo objects should be hashable via id field for set deduplication."""
    # Using same id with same content should deduplicate in a set
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="a", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    todo_set = {todo1, todo2}
    # Equal objects should result in a set with only 1 element
    assert len(todo_set) == 1, f"Set of equal todos should have 1 element, got {len(todo_set)}"


def test_todo_not_equal_to_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="a", done=False)
    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "a"}
