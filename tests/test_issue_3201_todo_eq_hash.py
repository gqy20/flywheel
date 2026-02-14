"""Tests for Todo.__eq__ and __hash__ methods (Issue #3201).

These tests verify that:
1. Todo objects with same field values are equal
2. Todo objects can be compared for inequality
3. Todo objects can be used in sets for deduplication
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_values_returns_true() -> None:
    """Two Todos with identical field values should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    assert todo1 == todo2


def test_todo_eq_different_id_returns_false() -> None:
    """Todos with different id values should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=2, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    assert todo1 != todo2


def test_todo_eq_different_text_returns_false() -> None:
    """Todos with different text values should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy bread", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    assert todo1 != todo2


def test_todo_eq_different_done_returns_false() -> None:
    """Todos with different done values should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=True, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    assert todo1 != todo2


def test_todo_eq_different_type_returns_false() -> None:
    """Todo compared with non-Todo should return False (not raise)."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != "not a todo"
    assert todo != 1
    assert todo is not None
    assert todo != {"id": 1, "text": "buy milk"}


def test_todo_hash_same_id_in_set_deduplicates() -> None:
    """Todos with same id should be deduplicated in a set."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    todo_set = {todo1, todo2}

    assert len(todo_set) == 1


def test_todo_hash_different_id_in_set_keeps_both() -> None:
    """Todos with different ids should both be kept in a set."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=2, text="buy bread", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    todo_set = {todo1, todo2}

    assert len(todo_set) == 2


def test_todo_hash_usable_as_dict_key() -> None:
    """Todo should be usable as a dictionary key when fully equal."""
    timestamp = "2024-01-01T00:00:00+00:00"
    todo1 = Todo(id=1, text="task one", done=False, created_at=timestamp, updated_at=timestamp)
    todo2 = Todo(id=1, text="task one", done=False, created_at=timestamp, updated_at=timestamp)

    mapping = {todo1: "value1"}

    # Same todo (fully equal) should access same value
    assert mapping[todo2] == "value1"


def test_todo_eq_different_timestamps_returns_false() -> None:
    """Todos with different timestamps should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-02T00:00:00+00:00", updated_at="2024-01-01T00:00:00+00:00")

    assert todo1 != todo2
