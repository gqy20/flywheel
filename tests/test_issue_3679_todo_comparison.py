"""Tests for Todo comparison/sorting capability (Issue #3679).

These tests verify that:
1. Todo objects with the same id are equal (__eq__)
2. Todo objects with different ids are not equal
3. Todo objects can be sorted by created_at (__lt__)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id() -> None:
    """Todo objects with the same id should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="different text", done=True, created_at="2024-01-02T00:00:00+00:00")

    # Same id means equal regardless of other fields
    assert todo1 == todo2


def test_todo_inequality_different_id() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=2, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00")

    # Different id means not equal even if all other fields match
    assert todo1 != todo2


def test_todo_sort_by_created_at() -> None:
    """Todo objects should be sortable by created_at using sorted()."""
    todo_a = Todo(id=1, text="task a", done=False, created_at="2024-01-03T00:00:00+00:00")
    todo_b = Todo(id=2, text="task b", done=False, created_at="2024-01-01T00:00:00+00:00")
    todo_c = Todo(id=3, text="task c", done=False, created_at="2024-01-02T00:00:00+00:00")

    # Sort by created_at ascending
    sorted_todos = sorted([todo_a, todo_b, todo_c])

    # Should be ordered by created_at: b (Jan 1), c (Jan 2), a (Jan 3)
    assert sorted_todos[0].id == 2  # todo_b created first
    assert sorted_todos[1].id == 3  # todo_c created second
    assert sorted_todos[2].id == 1  # todo_a created last


def test_todo_not_equal_to_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="buy milk")

    # Should not be equal to other types
    assert todo != 1
    assert todo != "todo"
    assert todo != {"id": 1, "text": "buy milk"}
    assert todo is not None
