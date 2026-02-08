"""Tests for Todo.__eq__ and __hash__ methods (Issue #2210).

These tests verify that:
1. Todo objects can be properly compared using ==
2. Todo objects can be used in sets and as dict keys
3. Equality is based on all fields: id, text, done, created_at, updated_at
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_values() -> None:
    """Two Todo objects with same id, text, done, created_at, updated_at are equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    assert todo1 == todo2


def test_todo_inequality_different_id() -> None:
    """Todo objects with different ids are not equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=2, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    assert todo1 != todo2


def test_todo_inequality_different_text() -> None:
    """Todo objects with different text are not equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy bread", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    assert todo1 != todo2


def test_todo_inequality_different_done() -> None:
    """Todo objects with different done status are not equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=True, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    assert todo1 != todo2


def test_todo_inequality_different_created_at() -> None:
    """Todo objects with different created_at timestamps are not equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-02T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    assert todo1 != todo2


def test_todo_inequality_different_updated_at() -> None:
    """Todo objects with different updated_at timestamps are not equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-02T00:00:00+00:00")

    assert todo1 != todo2


def test_todo_hashable() -> None:
    """Todo objects can be used in sets and as dict keys."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo3 = Todo(id=2, text="buy bread", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    # Equal objects should hash the same
    assert hash(todo1) == hash(todo2)

    # Set should deduplicate equal todos
    todo_set = {todo1, todo2, todo3}
    assert len(todo_set) == 2

    # Can use as dict key
    todo_dict = {todo1: "first", todo3: "second"}
    assert todo_dict[todo2] == "first"  # todo2 == todo1
    assert todo_dict[todo3] == "second"


def test_todo_not_equal_to_other_types() -> None:
    """Todo is not equal to objects of other types."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != "buy milk"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk"}
    assert todo is not None


def test_todo_reflexive_equality() -> None:
    """Todo equality is reflexive: x == x."""
    todo = Todo(id=1, text="buy milk", done=False)
    assert todo == todo


def test_todo_symmetric_equality() -> None:
    """Todo equality is symmetric: if x == y then y == x."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_transitive_equality() -> None:
    """Todo equality is transitive: if x == y and y == z then x == z."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo3 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3
