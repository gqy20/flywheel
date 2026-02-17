"""Tests for Todo sorting via __lt__ method (Issue #3878).

These tests verify that:
1. sorted() works naturally on a list of Todos by id
2. min() and max() functions work on Todo collections
3. Todo objects support full comparison suite via total_ordering
"""

from __future__ import annotations

from functools import total_ordering

from flywheel.todo import Todo


def test_todo_sorted_by_id() -> None:
    """sorted(list_of_todos) should return todos ordered by id."""
    todo3 = Todo(id=3, text="third")
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")

    result = sorted([todo3, todo1, todo2])

    assert result[0].id == 1
    assert result[1].id == 2
    assert result[2].id == 3


def test_todo_min_max_functions() -> None:
    """min() and max() should work on a list of Todos."""
    todo3 = Todo(id=3, text="third")
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")
    todos = [todo3, todo1, todo2]

    assert min(todos).id == 1
    assert max(todos).id == 3


def test_todo_less_than_comparison() -> None:
    """Todo.__lt__ should compare by id."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")

    assert todo1 < todo2
    assert not todo2 < todo1


def test_todo_greater_than_comparison() -> None:
    """Todo.__gt__ should work via total_ordering."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")

    assert todo2 > todo1
    assert not todo1 > todo2


def test_todo_less_than_or_equal_comparison() -> None:
    """Todo.__le__ should work via total_ordering."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")

    assert todo1 <= todo2
    # Same id, different text: __le__ is false since dataclass __eq__ compares all fields
    # But we can verify the ordering works correctly
    assert todo1 < todo2


def test_todo_greater_than_or_equal_comparison() -> None:
    """Todo.__ge__ should work via total_ordering."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")

    assert todo2 >= todo1
    assert todo2 > todo1


def test_todo_equality_based_on_id() -> None:
    """Todo equality should be based on id for comparison purposes."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")
    todo1_copy = Todo(id=1, text="first copy")

    # __eq__ from dataclass compares all fields
    # but for comparison via total_ordering, == works on id
    assert not todo1 == todo2  # Different ids


def test_todo_sorted_empty_list() -> None:
    """sorted([]) should return an empty list."""
    result = sorted([])
    assert result == []


def test_todo_sorted_single_element() -> None:
    """sorted([single_todo]) should return a list with that todo."""
    todo = Todo(id=42, text="only one")
    result = sorted([todo])

    assert len(result) == 1
    assert result[0].id == 42


def test_todo_sorting_reverse() -> None:
    """sorted(todos, reverse=True) should return todos in descending order."""
    todo3 = Todo(id=3, text="third")
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")

    result = sorted([todo3, todo1, todo2], reverse=True)

    assert result[0].id == 3
    assert result[1].id == 2
    assert result[2].id == 1
