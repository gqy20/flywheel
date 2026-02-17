"""Tests for Todo comparison methods (Issue #3878).

These tests verify that:
1. sorted() works naturally on a list of Todos by id
2. min()/max() functions work on a list of Todos
3. Comparison operators work correctly
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_lt_comparison_by_id() -> None:
    """Todo __lt__ should compare by id."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")

    assert todo1 < todo2
    assert not todo2 < todo1


def test_todo_sorted_natural_order() -> None:
    """sorted(list_of_todos) should return todos ordered by id."""
    todo3 = Todo(id=3, text="third")
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")

    result = sorted([todo3, todo1, todo2])

    assert result == [todo1, todo2, todo3]
    assert result[0].id == 1
    assert result[1].id == 2
    assert result[2].id == 3


def test_todo_min_max_functions() -> None:
    """min() and max() should work on a list of Todos."""
    todo3 = Todo(id=3, text="third")
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")
    todos = [todo3, todo1, todo2]

    assert min(todos) == todo1
    assert max(todos) == todo3


def test_todo_equality_by_id() -> None:
    """Todo == and != should compare by id (from dataclass)."""
    todo1a = Todo(id=1, text="first")
    todo1b = Todo(id=1, text="different text")
    todo2 = Todo(id=2, text="first")

    # Same id, different text -> not equal (dataclass compares all fields)
    # This is expected dataclass behavior
    assert todo1a != todo1b  # dataclass compares all fields
    assert todo1a != todo2


def test_todo_total_ordering() -> None:
    """All comparison operators should work with total_ordering."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")
    todo3 = Todo(id=3, text="third")

    # Test <=
    assert todo1 <= todo2
    assert todo1 <= todo1  # same object

    # Test >=
    assert todo2 >= todo1
    assert todo2 >= todo2  # same object

    # Test >
    assert todo2 > todo1
    assert todo3 > todo2
