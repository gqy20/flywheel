"""Tests for Todo.__eq__ method (Issue #6094).

These tests verify that:
1. Todo objects with same id/text/done are equal (even with different timestamps)
2. Todo objects with different id/text/done are not equal
3. Todo equality comparison excludes timestamps
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_core_fields_equal() -> None:
    """Two Todo objects with same id/text/done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-12-31", updated_at="2024-12-31")

    assert todo1 == todo2


def test_todo_eq_different_id_not_equal() -> None:
    """Two Todo objects with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2


def test_todo_eq_different_text_not_equal() -> None:
    """Two Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2


def test_todo_eq_different_done_not_equal() -> None:
    """Two Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2


def test_todo_eq_with_non_todo_not_equal() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk", "done": False}
    assert todo is not None


def test_todo_eq_reflexive() -> None:
    """A Todo should be equal to itself."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo == todo


def test_todo_eq_symmetric() -> None:
    """Equality should be symmetric (a == b implies b == a)."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-12-31")

    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_eq_transitive() -> None:
    """Equality should be transitive (a == b and b == c implies a == c)."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-06-01")
    todo3 = Todo(id=1, text="buy milk", done=False, created_at="2024-12-31")

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3


def test_todo_eq_works_in_set() -> None:
    """Todo equality should work correctly in sets."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-12-31")
    todo3 = Todo(id=2, text="buy bread", done=False)

    # Since todo1 and todo2 are equal, set should have only 2 unique elements
    todo_set = {todo1, todo2, todo3}

    assert len(todo_set) == 2
