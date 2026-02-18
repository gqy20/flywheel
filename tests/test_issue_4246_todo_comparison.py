"""Tests for Todo comparison/sorting support (Issue #4246).

These tests verify that:
1. Todo objects are comparable via __lt__ for sorting
2. sorted(todos) works as expected
3. Sorting prioritizes undone todos, then by created_at timestamp
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_lt_not_done_before_done() -> None:
    """Undone todos should come before done todos in sorting."""
    todo_done = Todo(id=1, text="done task", done=True, created_at="2024-01-01T00:00:00+00:00")
    todo_undone = Todo(
        id=2, text="pending task", done=False, created_at="2024-01-02T00:00:00+00:00"
    )

    # Undone should be "less than" done (comes first when sorted)
    assert todo_undone < todo_done


def test_todo_lt_both_undone_earlier_created_first() -> None:
    """When both todos are undone, earlier created_at should come first."""
    todo_earlier = Todo(id=1, text="earlier", done=False, created_at="2024-01-01T00:00:00+00:00")
    todo_later = Todo(id=2, text="later", done=False, created_at="2024-01-02T00:00:00+00:00")

    assert todo_earlier < todo_later


def test_todo_lt_both_done_earlier_created_first() -> None:
    """When both todos are done, earlier created_at should come first."""
    todo_earlier = Todo(id=1, text="earlier", done=True, created_at="2024-01-01T00:00:00+00:00")
    todo_later = Todo(id=2, text="later", done=True, created_at="2024-01-02T00:00:00+00:00")

    assert todo_earlier < todo_later


def test_sorted_todos_basic() -> None:
    """sorted(todos) should work and return a sorted list."""
    todo1 = Todo(id=1, text="task 1", done=False, created_at="2024-01-03T00:00:00+00:00")
    todo2 = Todo(id=2, text="task 2", done=False, created_at="2024-01-01T00:00:00+00:00")
    todo3 = Todo(id=3, text="task 3", done=True, created_at="2024-01-02T00:00:00+00:00")

    todos = [todo1, todo2, todo3]
    sorted_todos = sorted(todos)

    # Undone first, sorted by created_at; done last
    assert sorted_todos[0].id == 2  # undone, earliest created
    assert sorted_todos[1].id == 1  # undone, later created
    assert sorted_todos[2].id == 3  # done


def test_sorted_todos_mixed_status() -> None:
    """sorted() should prioritize undone todos over done regardless of time."""
    done_early = Todo(id=1, text="done early", done=True, created_at="2024-01-01T00:00:00+00:00")
    undone_late = Todo(id=2, text="undone late", done=False, created_at="2024-12-01T00:00:00+00:00")

    todos = [done_early, undone_late]
    sorted_todos = sorted(todos)

    # Undone should come first even though it was created later
    assert sorted_todos[0].id == 2
    assert sorted_todos[1].id == 1


def test_todo_comparison_equality() -> None:
    """Todo objects should still work with equality (dataclass default)."""
    todo1 = Todo(id=1, text="task", done=False, created_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="task", done=False, created_at="2024-01-01T00:00:00+00:00")
    todo3 = Todo(id=2, text="task", done=False, created_at="2024-01-01T00:00:00+00:00")

    # Dataclass provides __eq__ by default
    assert todo1 == todo2
    assert todo1 != todo3
