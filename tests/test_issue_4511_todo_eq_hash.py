"""Tests for Todo.__eq__ and __hash__ methods (Issue #4511).

These tests verify that:
1. Todo objects with same fields compare equal
2. Todo objects with different id compare not equal
3. Todo objects can be used in sets and as dict keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_fields() -> None:
    """Todo objects with identical fields should be equal."""
    # Use same timestamps to ensure equality test focuses on core fields
    ts = "2026-01-01T00:00:00+00:00"
    todo1 = Todo(id=1, text="buy milk", done=False, created_at=ts, updated_at=ts)
    todo2 = Todo(id=1, text="buy milk", done=False, created_at=ts, updated_at=ts)

    assert todo1 == todo2, "Todos with same fields should be equal"


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

    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk", "done": False}
    assert todo is not None


def test_todo_hash_consistent() -> None:
    """hash(Todo) should return consistent values for equal objects."""
    ts = "2026-01-01T00:00:00+00:00"
    todo1 = Todo(id=1, text="buy milk", done=False, created_at=ts, updated_at=ts)
    todo2 = Todo(id=1, text="buy milk", done=False, created_at=ts, updated_at=ts)

    assert hash(todo1) == hash(todo2), "Equal todos should have same hash"


def test_todo_hash_usable_in_set() -> None:
    """Todo objects should be usable in a set for deduplication."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)  # Same as todo1
    todo3 = Todo(id=2, text="buy bread", done=False)

    todo_set = {todo1, todo2, todo3}

    # Since todo1 and todo2 are equal with same hash, set should have 2 items
    assert len(todo_set) == 2, "Set should deduplicate equal todos"


def test_todo_hash_usable_as_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)  # Same as todo1
    todo3 = Todo(id=2, text="buy bread", done=False)

    todo_dict = {todo1: "first", todo2: "second", todo3: "third"}

    # Since todo1 and todo2 are equal with same hash, dict should have 2 items
    assert len(todo_dict) == 2, "Dict should deduplicate equal todo keys"

    # todo2 should overwrite todo1's value
    assert todo_dict[todo1] == "second"
