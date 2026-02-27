"""Tests for Todo.__eq__ method (Issue #6094).

These tests verify that:
1. Todo objects with same id/text/done are equal regardless of timestamps
2. Todo objects with different id are not equal
3. Todo objects with different text are not equal
4. Todo objects with different done status are not equal
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_core_fields_different_timestamps() -> None:
    """Todo objects with same id/text/done should be equal regardless of timestamps."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-12-31T23:59:59+00:00", updated_at="2024-12-31T23:59:59+00:00")

    assert todo1 == todo2, "Todos with same id/text/done should be equal regardless of timestamps"


def test_todo_eq_different_id() -> None:
    """Todo objects with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2, "Todos with different id should not be equal"


def test_todo_eq_different_text() -> None:
    """Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2, "Todos with different text should not be equal"


def test_todo_eq_different_done() -> None:
    """Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2, "Todos with different done status should not be equal"


def test_todo_eq_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != "Todo(id=1, text='buy milk', done=False)", "Todo should not equal a string"
    assert todo != {"id": 1, "text": "buy milk", "done": False}, "Todo should not equal a dict"
    assert todo != 1, "Todo should not equal an int"
    assert todo is not None, "Todo should not equal None"


def test_todo_eq_reflexive() -> None:
    """A Todo should equal itself."""
    todo = Todo(id=1, text="buy milk", done=False)
    assert todo == todo, "A Todo should equal itself"


def test_todo_eq_symmetric() -> None:
    """Equality should be symmetric: a == b implies b == a."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2, "todo1 should equal todo2"
    assert todo2 == todo1, "todo2 should equal todo1 (symmetry)"


def test_todo_eq_transitive() -> None:
    """Equality should be transitive: a == b and b == c implies a == c."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-06-01T00:00:00+00:00")
    todo3 = Todo(id=1, text="buy milk", done=False, created_at="2024-12-01T00:00:00+00:00")

    assert todo1 == todo2, "todo1 should equal todo2"
    assert todo2 == todo3, "todo2 should equal todo3"
    assert todo1 == todo3, "todo1 should equal todo3 (transitivity)"


def test_todo_hash_consistency() -> None:
    """Equal objects should have the same hash for use in sets/dicts."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-12-01T00:00:00+00:00")

    # If objects are equal, they should have the same hash
    if todo1 == todo2:
        assert hash(todo1) == hash(todo2), "Equal todos should have the same hash"


def test_todo_in_set() -> None:
    """Todo objects should work correctly in sets."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)  # Same as todo1
    todo3 = Todo(id=2, text="buy bread", done=False)  # Different

    todo_set = {todo1, todo2, todo3}

    # Set should contain 2 unique todos (todo1 and todo2 are equal)
    assert len(todo_set) == 2, f"Set should contain 2 unique todos, got {len(todo_set)}"
