"""Tests for Todo comparison capabilities (Issue #5916).

These tests verify that:
1. Todo objects can be compared for equality (__eq__)
2. Todo objects can be sorted (__lt__)
3. Todo objects can be placed in sets/dicts (__hash__)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id_text_done() -> None:
    """Todo objects with same id, text, and done should be equal."""
    # Use explicit timestamps to ensure equality comparison works
    ts = "2026-01-01T00:00:00+00:00"
    todo1 = Todo(id=1, text="buy milk", done=False, created_at=ts, updated_at=ts)
    todo2 = Todo(id=1, text="buy milk", done=False, created_at=ts, updated_at=ts)

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


def test_todo_sorting_by_id() -> None:
    """Todo objects should be sortable by id using sorted()."""
    todo1 = Todo(id=1, text="first", done=False)
    todo2 = Todo(id=3, text="third", done=False)
    todo3 = Todo(id=2, text="second", done=False)

    todos = [todo2, todo3, todo1]
    sorted_todos = sorted(todos)

    assert sorted_todos[0].id == 1
    assert sorted_todos[1].id == 2
    assert sorted_todos[2].id == 3


def test_todo_sorting_with_same_id() -> None:
    """Todo sorting should be stable when ids are equal."""
    todo1 = Todo(id=1, text="first", done=False)
    todo2 = Todo(id=1, text="second", done=True)

    todos = [todo2, todo1]
    sorted_todos = sorted(todos)

    # Both have same id, so order is preserved or deterministic
    assert len(sorted_todos) == 2


def test_todo_in_set() -> None:
    """Todo objects should be placeable in a set without TypeError."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy bread", done=False)

    # This should not raise TypeError: unhashable type: 'Todo'
    todo_set = {todo1, todo2}
    assert len(todo_set) == 2


def test_todo_set_deduplication() -> None:
    """Set should deduplicate equal Todo objects."""
    # Use explicit timestamps to ensure equality comparison works
    ts = "2026-01-01T00:00:00+00:00"
    todo1 = Todo(id=1, text="buy milk", done=False, created_at=ts, updated_at=ts)
    todo2 = Todo(id=1, text="buy milk", done=False, created_at=ts, updated_at=ts)

    todo_set = {todo1, todo2}
    # Equal objects should be deduplicated
    assert len(todo_set) == 1


def test_todo_as_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy bread", done=False)

    # This should not raise TypeError: unhashable type: 'Todo'
    todo_dict = {todo1: "first", todo2: "second"}
    assert todo_dict[todo1] == "first"
    assert todo_dict[todo2] == "second"


def test_todo_comparison_not_implemented_for_non_todo() -> None:
    """Todo comparison with non-Todo should return NotImplemented or False."""
    todo = Todo(id=1, text="buy milk", done=False)

    # Comparing with non-Todo should return False (not equal)
    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk"}
