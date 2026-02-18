"""Tests for Todo.__eq__ and __hash__ methods (Issue #4217).

These tests verify that:
1. Todo objects with same business fields (id, text, done) are equal
2. Timestamps (created_at, updated_at) do not affect equality
3. Todo objects can be used in sets and as dict keys (hashable)
4. Different id/text/done values produce unequal objects
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_business_fields() -> None:
    """Two Todo objects with same id, text, done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)
    assert todo1 == todo2


def test_todo_eq_ignores_timestamps() -> None:
    """Equality should ignore created_at and updated_at differences."""
    todo1 = Todo(
        id=1,
        text="buy milk",
        done=False,
        created_at="2024-01-01T00:00:00+00:00",
        updated_at="2024-01-01T00:00:00+00:00",
    )
    todo2 = Todo(
        id=1,
        text="buy milk",
        done=False,
        created_at="2024-12-31T23:59:59+00:00",
        updated_at="2024-12-31T23:59:59+00:00",
    )
    assert todo1 == todo2


def test_todo_eq_different_id() -> None:
    """Todo objects with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)
    assert todo1 != todo2


def test_todo_eq_different_text() -> None:
    """Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)
    assert todo1 != todo2


def test_todo_eq_different_done() -> None:
    """Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)
    assert todo1 != todo2


def test_todo_eq_not_todo_type() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="buy milk", done=False)
    assert todo != "Todo(id=1, text='buy milk', done=False)"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk", "done": False}


def test_todo_hash_based_on_id() -> None:
    """Todo objects should be hashable based on id."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00")
    assert hash(todo1) == hash(todo2)


def test_todo_in_set() -> None:
    """Todo objects should work in sets for deduplication."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-12-31T23:59:59+00:00")
    todo3 = Todo(id=2, text="buy bread", done=False)

    todo_set = {todo1, todo2, todo3}
    # todo1 and todo2 should be considered the same, so only 2 unique todos
    assert len(todo_set) == 2


def test_todo_as_dict_key() -> None:
    """Todo objects should work as dictionary keys."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-12-31T23:59:59+00:00")

    data = {todo1: "value1"}
    data[todo2] = "value2"

    # Since todo1 == todo2 and hash(todo1) == hash(todo2), this should overwrite
    assert len(data) == 1
    assert data[todo1] == "value2"
