"""Tests for Todo comparison methods (__eq__ and __lt__).

Issue #6480: Add comparison methods to Todo dataclass for sorting and deduplication.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_based_on_id() -> None:
    """Two Todos with the same id should be equal regardless of other fields."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_inequality_different_ids() -> None:
    """Two Todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")
    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_less_than_based_on_id() -> None:
    """Todo comparison should be based on id."""
    todo1 = Todo(id=1, text="z")
    todo3 = Todo(id=3, text="a")
    assert todo1 < todo3, "Todo with lower id should be less than"


def test_todo_sorting() -> None:
    """A list of Todos should be sortable by id."""
    todos = [Todo(id=3, text="c"), Todo(id=1, text="a"), Todo(id=2, text="b")]
    sorted_todos = sorted(todos)
    assert [t.id for t in sorted_todos] == [1, 2, 3], "Todos should be sorted by id"


def test_todo_set_deduplication() -> None:
    """A set of Todos should deduplicate based on id."""
    todo1 = Todo(id=1, text="a")
    todo1_dup = Todo(id=1, text="b")
    todo_set = {todo1, todo1_dup}
    assert len(todo_set) == 1, "Set should deduplicate Todos with same id"


def test_todo_not_equal_to_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="a")
    assert todo != 1, "Todo should not equal an integer"
    assert todo != "1", "Todo should not equal a string"
    assert todo != {"id": 1, "text": "a"}, "Todo should not equal a dict"
