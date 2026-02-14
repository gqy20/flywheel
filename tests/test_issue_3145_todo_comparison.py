"""Tests for issue #3145: Todo class __eq__ and __lt__ methods for sorting/comparison."""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_based_on_id() -> None:
    """Issue #3145: Two Todos with same id should be equal regardless of timestamps."""
    todo1 = Todo(id=1, text="task a")
    todo2 = Todo(id=1, text="task a")

    assert todo1 == todo2


def test_todo_inequality_different_id() -> None:
    """Issue #3145: Todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="task")
    todo2 = Todo(id=2, text="task")

    assert todo1 != todo2


def test_todo_less_than_based_on_id() -> None:
    """Issue #3145: todo1 < todo2 should compare by id."""
    todo1 = Todo(id=1, text="task a")
    todo2 = Todo(id=2, text="task b")

    assert todo1 < todo2
    assert not (todo2 < todo1)


def test_sorted_todos_by_id() -> None:
    """Issue #3145: sorted([todo3, todo1, todo2]) should return [todo1, todo2, todo3]."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")
    todo3 = Todo(id=3, text="third")

    sorted_todos = sorted([todo3, todo1, todo2])

    assert sorted_todos[0].id == 1
    assert sorted_todos[1].id == 2
    assert sorted_todos[2].id == 3


def test_list_sort_todos() -> None:
    """Issue #3145: list.sort() should work on Todo objects."""
    todos = [
        Todo(id=5, text="fifth"),
        Todo(id=1, text="first"),
        Todo(id=3, text="third"),
    ]

    todos.sort()

    assert todos[0].id == 1
    assert todos[1].id == 3
    assert todos[2].id == 5


def test_todo_comparison_same_id_different_text() -> None:
    """Issue #3145: Todos with same id compare equal regardless of text."""
    todo1 = Todo(id=1, text="alpha")
    todo2 = Todo(id=1, text="beta")

    # Same id means equal, comparison for sorting still works by id
    assert todo1 == todo2
    assert not (todo1 < todo2)
    assert not (todo2 < todo1)
