"""Tests for Todo comparison and sorting (Issue #3145).

Regression tests for adding __eq__ and __lt__ methods to Todo class.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_lt_comparison_by_id() -> None:
    """Todo instances should be comparable by id using < operator."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")

    assert todo1 < todo2
    assert not todo2 < todo1


def test_todo_gt_comparison_by_id() -> None:
    """Todo instances should be comparable by id using > operator."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")

    assert todo2 > todo1
    assert not todo1 > todo2


def test_todo_sorted_by_id() -> None:
    """sorted() should return Todos ordered by id."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")
    todo3 = Todo(id=3, text="third")

    unsorted = [todo3, todo1, todo2]
    result = sorted(unsorted)

    assert result == [todo1, todo2, todo3]
    assert result[0].id == 1
    assert result[1].id == 2
    assert result[2].id == 3


def test_todo_list_sort_by_id() -> None:
    """list.sort() should sort Todos in place by id."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")
    todo3 = Todo(id=3, text="third")

    todos = [todo3, todo1, todo2]
    todos.sort()

    assert todos[0].id == 1
    assert todos[1].id == 2
    assert todos[2].id == 3


def test_todo_equality_same_id_and_text() -> None:
    """Two Todo instances with same id and text should be equal."""
    todo_a = Todo(id=1, text="task")
    todo_b = Todo(id=1, text="task")

    assert todo_a == todo_b


def test_todo_equality_with_different_timestamps() -> None:
    """Todos with same id and text should be equal regardless of timestamps."""
    todo_a = Todo(id=1, text="task", created_at="2024-01-01T00:00:00Z")
    todo_b = Todo(id=1, text="task", created_at="2024-12-31T23:59:59Z")

    assert todo_a == todo_b


def test_todo_inequality_different_id() -> None:
    """Two Todo instances with different id should not be equal."""
    todo_a = Todo(id=1, text="task")
    todo_b = Todo(id=2, text="task")

    assert todo_a != todo_b


def test_todo_inequality_different_text() -> None:
    """Two Todo instances with different text should not be equal."""
    todo_a = Todo(id=1, text="task a")
    todo_b = Todo(id=1, text="task b")

    assert todo_a != todo_b


def test_todo_inequality_different_done() -> None:
    """Todos with same id/text but different done status should still be equal.

    Note: Equality is based on id and text only, not on done/timestamps.
    This allows finding todos in collections by their identity.
    """
    todo_a = Todo(id=1, text="task")
    todo_b = Todo(id=1, text="task")

    todo_a.mark_done()

    # Both have same id and text, so they should be equal
    assert todo_a == todo_b


def test_todo_le_comparison() -> None:
    """Todo instances should support <= comparison."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")

    assert todo1 <= todo2
    assert todo1 <= todo1  # Same id is <=


def test_todo_ge_comparison() -> None:
    """Todo instances should support >= comparison."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")

    assert todo2 >= todo1
    assert todo1 >= todo1  # Same id is >=
