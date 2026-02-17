"""Tests for Todo comparison methods (Issue #3878).

These tests verify that:
1. Todo objects can be sorted by id using sorted()
2. Todo objects work with min()/max() functions
3. Todo objects support comparison operators (<, <=, >, >=, ==, !=)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoComparison:
    """Test suite for Todo comparison methods."""

    def test_sorted_returns_todos_in_id_order(self) -> None:
        """sorted([todo3, todo1, todo2]) should return [todo1, todo2, todo3] by id."""
        todo1 = Todo(id=1, text="first")
        todo2 = Todo(id=2, text="second")
        todo3 = Todo(id=3, text="third")

        # Sort in reverse order
        result = sorted([todo3, todo1, todo2])

        assert len(result) == 3
        assert result[0].id == 1
        assert result[1].id == 2
        assert result[2].id == 3

    def test_min_function_works_on_todo_list(self) -> None:
        """min() should return the Todo with smallest id."""
        todo1 = Todo(id=1, text="first")
        todo2 = Todo(id=2, text="second")
        todo3 = Todo(id=3, text="third")

        result = min([todo3, todo1, todo2])
        assert result.id == 1

    def test_max_function_works_on_todo_list(self) -> None:
        """max() should return the Todo with largest id."""
        todo1 = Todo(id=1, text="first")
        todo2 = Todo(id=2, text="second")
        todo3 = Todo(id=3, text="third")

        result = max([todo3, todo1, todo2])
        assert result.id == 3

    def test_less_than_operator(self) -> None:
        """Todo comparison by < should compare by id."""
        todo1 = Todo(id=1, text="first")
        todo2 = Todo(id=2, text="second")

        assert todo1 < todo2
        assert not todo2 < todo1
        assert not todo1 < todo1  # Same id is not less than itself

    def test_greater_than_operator(self) -> None:
        """Todo comparison by > should compare by id."""
        todo1 = Todo(id=1, text="first")
        todo2 = Todo(id=2, text="second")

        assert todo2 > todo1
        assert not todo1 > todo2
        assert not todo2 > todo2  # Same id is not greater than itself

    def test_less_than_or_equal_operator(self) -> None:
        """Todo comparison by <= should compare by id."""
        todo1 = Todo(id=1, text="first")
        todo2 = Todo(id=2, text="second")

        assert todo1 <= todo2
        assert todo1 <= todo1  # Same id should be equal
        assert not todo2 <= todo1

    def test_greater_than_or_equal_operator(self) -> None:
        """Todo comparison by >= should compare by id."""
        todo1 = Todo(id=1, text="first")
        todo2 = Todo(id=2, text="second")

        assert todo2 >= todo1
        assert todo2 >= todo2  # Same id should be equal
        assert not todo1 >= todo2

    def test_sorting_single_element(self) -> None:
        """Sorting a single-element list should work."""
        todo = Todo(id=42, text="solo")
        result = sorted([todo])

        assert len(result) == 1
        assert result[0].id == 42

    def test_sorting_empty_list(self) -> None:
        """Sorting an empty list should return empty list."""
        result: list[Todo] = sorted([])
        assert result == []

    def test_sorting_with_non_sequential_ids(self) -> None:
        """Sorting should work with non-sequential ids."""
        todo100 = Todo(id=100, text="hundred")
        todo5 = Todo(id=5, text="five")
        todo50 = Todo(id=50, text="fifty")

        result = sorted([todo100, todo5, todo50])

        assert result[0].id == 5
        assert result[1].id == 50
        assert result[2].id == 100

    def test_sorting_reverse(self) -> None:
        """reverse=True should work with sorted()."""
        todo1 = Todo(id=1, text="first")
        todo2 = Todo(id=2, text="second")
        todo3 = Todo(id=3, text="third")

        result = sorted([todo1, todo2, todo3], reverse=True)

        assert result[0].id == 3
        assert result[1].id == 2
        assert result[2].id == 1
