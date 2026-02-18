"""Tests for Todo comparison support (Issue #4246).

These tests verify that:
1. Todo objects are comparable (support __lt__)
2. sorted(todos) orders by done status (incomplete first) then created_at
3. Comparison handles edge cases (same timestamps, missing timestamps)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_supports_less_than() -> None:
    """Todo objects should support < comparison."""
    todo1 = Todo(id=1, text="task one", done=False, created_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=2, text="task two", done=False, created_at="2024-01-02T00:00:00+00:00")

    # Should not raise TypeError
    result = todo1 < todo2
    assert isinstance(result, bool)


def test_sorted_todos_by_created_at() -> None:
    """sorted(todos) should order by created_at (older first) when same done status."""
    todo1 = Todo(id=1, text="later task", done=False, created_at="2024-01-02T00:00:00+00:00")
    todo2 = Todo(id=2, text="earlier task", done=False, created_at="2024-01-01T00:00:00+00:00")

    result = sorted([todo1, todo2])

    assert result[0].id == 2  # earlier task first
    assert result[1].id == 1


def test_sorted_todos_incomplete_before_complete() -> None:
    """sorted(todos) should place incomplete todos before completed ones."""
    complete = Todo(id=1, text="done task", done=True, created_at="2024-01-01T00:00:00+00:00")
    incomplete = Todo(id=2, text="pending task", done=False, created_at="2024-01-02T00:00:00+00:00")

    result = sorted([complete, incomplete])

    assert result[0].done is False  # incomplete first
    assert result[1].done is True


def test_sorted_todos_done_status_priority_over_created_at() -> None:
    """Incomplete todos should come before completed ones regardless of created_at."""
    # Completed task created earlier
    complete_early = Todo(
        id=1, text="done early", done=True, created_at="2024-01-01T00:00:00+00:00"
    )
    # Incomplete task created later
    incomplete_late = Todo(
        id=2, text="pending late", done=False, created_at="2024-01-02T00:00:00+00:00"
    )

    result = sorted([complete_early, incomplete_late])

    # Incomplete should still come first even though it was created later
    assert result[0].id == 2
    assert result[1].id == 1


def test_sorted_todos_with_same_created_at_uses_id_as_tiebreaker() -> None:
    """When created_at is identical, use id as tiebreaker for consistent ordering."""
    todo1 = Todo(id=1, text="first", done=False, created_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=2, text="second", done=False, created_at="2024-01-01T00:00:00+00:00")

    result = sorted([todo2, todo1])

    # Lower id should come first when timestamps are equal
    assert result[0].id == 1
    assert result[1].id == 2


def test_sorted_todos_mixed_statuses_and_times() -> None:
    """Comprehensive test with multiple todos of different statuses and times."""
    todos = [
        Todo(id=4, text="done late", done=True, created_at="2024-01-04T00:00:00+00:00"),
        Todo(id=1, text="pending early", done=False, created_at="2024-01-01T00:00:00+00:00"),
        Todo(id=3, text="done early", done=True, created_at="2024-01-02T00:00:00+00:00"),
        Todo(id=2, text="pending late", done=False, created_at="2024-01-03T00:00:00+00:00"),
    ]

    result = sorted(todos)

    # All incomplete first (sorted by created_at), then all complete (sorted by created_at)
    assert result[0].id == 1  # pending early
    assert result[1].id == 2  # pending late
    assert result[2].id == 3  # done early
    assert result[3].id == 4  # done late
