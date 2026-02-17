"""Tests for Todo __eq__ and __hash__ methods (Issue #4008).

These tests verify that:
1. Todo objects with same fields compare as equal
2. Todo objects with different fields compare as not equal
3. Todo objects can be hashed and used in sets/dicts
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_fields() -> None:
    """Todo(1, 'a') == Todo(1, 'a') should return True when timestamps match."""
    # Use explicit timestamps to avoid race conditions in equality comparison
    timestamp = "2024-01-01T00:00:00+00:00"
    todo1 = Todo(id=1, text="a", done=False, created_at=timestamp, updated_at=timestamp)
    todo2 = Todo(id=1, text="a", done=False, created_at=timestamp, updated_at=timestamp)

    assert todo1 == todo2


def test_todo_eq_same_fields_with_timestamps() -> None:
    """Todo objects with same timestamps should be equal."""
    timestamp = "2024-01-01T00:00:00+00:00"
    todo1 = Todo(id=1, text="task", done=True, created_at=timestamp, updated_at=timestamp)
    todo2 = Todo(id=1, text="task", done=True, created_at=timestamp, updated_at=timestamp)

    assert todo1 == todo2


def test_todo_neq_different_id() -> None:
    """Todo(1, 'a') != Todo(2, 'a') should return True."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=2, text="a", done=False)

    assert todo1 != todo2


def test_todo_neq_different_text() -> None:
    """Todos with different text should not be equal."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="b", done=False)

    assert todo1 != todo2


def test_todo_neq_different_done() -> None:
    """Todos with different done status should not be equal."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=True)

    assert todo1 != todo2


def test_todo_neq_different_timestamps() -> None:
    """Todos with different timestamps should not be equal."""
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="a", done=False, created_at="2024-01-02T00:00:00+00:00")

    assert todo1 != todo2


def test_todo_hash_is_hashable() -> None:
    """hash(Todo) should not raise TypeError."""
    todo = Todo(id=1, text="a")

    # Should not raise TypeError
    _ = hash(todo)


def test_todo_hash_in_set() -> None:
    """Todo objects should be usable in sets."""
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="a", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo3 = Todo(id=2, text="b", done=False)

    todo_set = {todo1, todo2, todo3}

    # Since todo1 == todo2 and hash(todo1) == hash(todo2), set should have 2 items
    assert len(todo_set) == 2


def test_todo_hash_as_dict_key() -> None:
    """Todo objects should be usable as dict keys."""
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="a", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    todo_dict = {todo1: "first"}

    # Since todo1 == todo2, looking up todo2 should return "first"
    assert todo_dict[todo2] == "first"


def test_todo_eq_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="a")

    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "a"}
    assert todo is not None
