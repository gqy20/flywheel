"""Tests for Todo sorting/comparison support (Issue #4246).

These tests verify that:
1. Todo objects support comparison via __lt__ for sorting
2. Todo objects support __eq__ for equality comparison
3. sorted(todos) works and sorts by created_at with pending first
4. The default sort order prioritizes pending (not done) items
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_lt_by_created_at() -> None:
    """Todo objects should be comparable by created_at timestamp."""
    todo1 = Todo(id=1, text="first", done=False, created_at="2024-01-01T00:00:00Z")
    todo2 = Todo(id=2, text="second", done=False, created_at="2024-01-02T00:00:00Z")

    # Earlier todo should be "less than" later todo
    assert todo1 < todo2
    assert not todo2 < todo1


def test_todo_eq_by_id() -> None:
    """Todo objects with same id should be equal."""
    todo1 = Todo(id=1, text="same id", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    # Same id means equal
    assert todo1 == todo2


def test_todo_eq_different_id() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text", done=True)
    todo2 = Todo(id=2, text="same text", done=True)

    assert todo1 != todo2


def test_todo_sort_by_created_at() -> None:
    """sorted(todos) should sort by created_at ascending."""
    todo1 = Todo(id=1, text="first", done=False, created_at="2024-01-03T00:00:00Z")
    todo2 = Todo(id=2, text="second", done=False, created_at="2024-01-01T00:00:00Z")
    todo3 = Todo(id=3, text="third", done=False, created_at="2024-01-02T00:00:00Z")

    todos = [todo1, todo2, todo3]
    sorted_todos = sorted(todos)

    # Should be sorted by created_at ascending
    assert sorted_todos[0].id == 2  # 2024-01-01
    assert sorted_todos[1].id == 3  # 2024-01-02
    assert sorted_todos[2].id == 1  # 2024-01-03


def test_todo_sort_pending_first() -> None:
    """sorted(todos) should put pending items before done items."""
    # Create todos with same created_at but different done status
    todo1 = Todo(id=1, text="done task", done=True, created_at="2024-01-01T00:00:00Z")
    todo2 = Todo(id=2, text="pending task", done=False, created_at="2024-01-01T00:00:00Z")

    todos = [todo1, todo2]
    sorted_todos = sorted(todos)

    # Pending should come first
    assert sorted_todos[0].id == 2
    assert sorted_todos[0].done is False
    assert sorted_todos[1].id == 1
    assert sorted_todos[1].done is True


def test_todo_sort_pending_first_then_by_created_at() -> None:
    """sorted(todos) should prioritize pending, then sort by created_at."""
    todo1 = Todo(id=1, text="done early", done=True, created_at="2024-01-01T00:00:00Z")
    todo2 = Todo(id=2, text="done late", done=True, created_at="2024-01-03T00:00:00Z")
    todo3 = Todo(id=3, text="pending early", done=False, created_at="2024-01-01T00:00:00Z")
    todo4 = Todo(id=4, text="pending late", done=False, created_at="2024-01-03T00:00:00Z")

    todos = [todo1, todo2, todo3, todo4]
    sorted_todos = sorted(todos)

    # Pending first (sorted by created_at), then done (sorted by created_at)
    assert sorted_todos[0].id == 3  # pending early
    assert sorted_todos[1].id == 4  # pending late
    assert sorted_todos[2].id == 1  # done early
    assert sorted_todos[3].id == 2  # done late
