"""Tests for Todo.__eq__ and __hash__ methods (Issue #4217).

These tests verify that:
1. Todo objects compare equal based on business key fields (id, text, done)
2. Timestamps (created_at, updated_at) do not affect equality
3. Todo objects can be used in sets and as dict keys via __hash__
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_todo_eq_same_business_fields() -> None:
    """Two Todos with same id, text, done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=True)
    # Small delay to ensure different timestamps
    time.sleep(0.001)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 == todo2, "Todos with same business fields should be equal"


def test_todo_eq_ignores_timestamps() -> None:
    """Equality should ignore created_at and updated_at differences."""
    # Create two todos with same business fields but different timestamps
    todo1 = Todo(
        id=1,
        text="task",
        done=False,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
    )
    todo2 = Todo(
        id=1,
        text="task",
        done=False,
        created_at="2024-12-31T23:59:59Z",
        updated_at="2024-12-31T23:59:59Z",
    )

    assert todo1 == todo2, "Todos should be equal regardless of timestamps"


def test_todo_eq_different_id() -> None:
    """Two Todos with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2, "Todos with different id should not be equal"


def test_todo_eq_different_text() -> None:
    """Two Todos with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2, "Todos with different text should not be equal"


def test_todo_eq_different_done() -> None:
    """Two Todos with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2, "Todos with different done status should not be equal"


def test_todo_eq_with_non_todo() -> None:
    """Comparing Todo with non-Todo should return False."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk", "done": False}
    assert todo is not None


def test_todo_hash_same_business_fields() -> None:
    """Two Todos with same business fields should have same hash."""
    todo1 = Todo(id=1, text="buy milk", done=True, created_at="2024-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="buy milk", done=True, created_at="2024-12-31T23:59:59Z")

    assert hash(todo1) == hash(todo2), "Todos with same business fields should have same hash"


def test_todo_hash_allows_set_usage() -> None:
    """Todo objects should work in sets for deduplication."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-12-31T23:59:59Z")
    todo3 = Todo(id=2, text="buy bread", done=False)

    # Set should contain only 2 unique todos
    unique_todos = {todo1, todo2, todo3}
    assert len(unique_todos) == 2, f"Set should deduplicate equal todos, got {len(unique_todos)}"


def test_todo_hash_allows_dict_key_usage() -> None:
    """Todo objects should work as dict keys."""
    todo1 = Todo(id=1, text="buy milk", done=False, created_at="2024-01-01T00:00:00Z")
    todo2 = Todo(id=1, text="buy milk", done=False, created_at="2024-12-31T23:59:59Z")

    todo_dict = {todo1: "first"}
    # Overwrite with equivalent todo
    todo_dict[todo2] = "second"

    assert len(todo_dict) == 1, "Dict should have only one key for equal todos"
    assert todo_dict[todo1] == "second", "Value should be overwritten"
