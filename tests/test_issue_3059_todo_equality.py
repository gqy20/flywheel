"""Tests for Todo.__eq__ method (Issue #3059).

These tests verify that Todo objects support value-based equality
comparison based on id, text, and done fields, enabling proper
list membership tests, deduplication, and test assertions.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_values() -> None:
    """Todo objects with same id, text, and done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2


def test_todo_equality_different_id() -> None:
    """Todo objects with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_todo_equality_different_text() -> None:
    """Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2


def test_todo_equality_different_done() -> None:
    """Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2


def test_todo_equality_reflexive() -> None:
    """A Todo should equal itself."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo == todo


def test_todo_equality_symmetric() -> None:
    """Equality should be symmetric: if a == b then b == a."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_equality_transitive() -> None:
    """Equality should be transitive: if a == b and b == c then a == c."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    todo3 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3


def test_todo_equality_not_equal_to_none() -> None:
    """Todo should not be equal to None."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo is not None
    assert todo != None  # noqa: E711 - explicitly testing __eq__ with None


def test_todo_equality_not_equal_to_other_type() -> None:
    """Todo should not be equal to objects of other types."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != "Todo(id=1, text='buy milk', done=False)"
    assert todo != {"id": 1, "text": "buy milk", "done": False}


def test_todo_equality_with_done_true() -> None:
    """Todo equality should work correctly when done=True."""
    todo1 = Todo(id=1, text="completed task", done=True)
    todo2 = Todo(id=1, text="completed task", done=True)

    assert todo1 == todo2


def test_todo_equality_enables_list_membership() -> None:
    """Equality should enable proper list membership tests."""
    todo = Todo(id=1, text="buy milk", done=False)
    todo_list = [todo, Todo(id=2, text="buy bread", done=False)]

    # Create a new Todo with same values - should be found in list
    same_todo = Todo(id=1, text="buy milk", done=False)
    assert same_todo in todo_list


def test_todo_equality_enables_deduplication() -> None:
    """Equality should enable deduplication via set conversion."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)  # Duplicate
    todo3 = Todo(id=2, text="buy bread", done=False)

    todos = [todo1, todo2, todo3]
    unique_todos = list(set(todos))

    # After deduplication, should have 2 unique todos
    assert len(unique_todos) == 2
