"""Tests for Todo comparison/sorting capabilities (Issue #3679).

These tests verify that:
1. Todo objects can be compared by id using __eq__
2. Todo objects can be sorted by created_at using __lt__
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id() -> None:
    """Todo(id=1) == Todo(id=1) should return True."""
    todo1 = Todo(id=1, text="task one", done=False)
    todo2 = Todo(id=1, text="task two", done=True)

    # Same id means equal regardless of other fields
    assert todo1 == todo2


def test_todo_inequality_different_id() -> None:
    """Todo(id=1) != Todo(id=2) should return True."""
    todo1 = Todo(id=1, text="same task", done=False)
    todo2 = Todo(id=2, text="same task", done=False)

    # Different id means not equal
    assert todo1 != todo2


def test_todo_sort_by_created_at() -> None:
    """sorted() should order todos by created_at ascending."""
    # Create todos with explicit timestamps
    todo_a = Todo(id=1, text="first", created_at="2024-01-01T10:00:00+00:00")
    todo_b = Todo(id=2, text="second", created_at="2024-01-02T10:00:00+00:00")
    todo_c = Todo(id=3, text="third", created_at="2024-01-03T10:00:00+00:00")

    # Shuffle the order
    todos = [todo_c, todo_a, todo_b]
    sorted_todos = sorted(todos)

    # Should be in created_at order: todo_a, todo_b, todo_c
    assert sorted_todos[0].id == 1
    assert sorted_todos[1].id == 2
    assert sorted_todos[2].id == 3


def test_todo_lt_by_created_at() -> None:
    """todo_a < todo_b should compare by created_at."""
    todo_earlier = Todo(id=1, text="earlier", created_at="2024-01-01T10:00:00+00:00")
    todo_later = Todo(id=2, text="later", created_at="2024-01-02T10:00:00+00:00")

    assert todo_earlier < todo_later
    assert not (todo_later < todo_earlier)


def test_todo_hash_consistent_with_eq() -> None:
    """Todo objects with same id should have same hash for use in sets/dicts."""
    todo1 = Todo(id=1, text="task one", done=False)
    todo2 = Todo(id=1, text="task two", done=True)

    # Same id should produce same hash
    assert hash(todo1) == hash(todo2)

    # Should work in a set (deduplication by id)
    todo_set = {todo1, todo2}
    assert len(todo_set) == 1


def test_todo_equality_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="task", done=False)

    # Should not be equal to int, string, or None
    assert todo != 1
    assert todo != "task"
    assert todo != None  # noqa: E711
