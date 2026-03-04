"""Tests for Todo __eq__ and __hash__ methods (Issue #7262).

These tests verify that:
1. Todo objects with same id are equal regardless of other fields
2. Todo objects with different ids are not equal
3. Todo objects with same id have same hash
4. Todo objects can be used in sets for deduplication
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_by_id() -> None:
    """Todo objects with same id should be equal regardless of other fields."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy eggs", done=True)

    # Same id means equal
    assert todo1 == todo2


def test_todo_inequality_by_different_id() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    # Different id means not equal
    assert todo1 != todo2


def test_todo_hash_consistent() -> None:
    """Todo objects with same id should have same hash."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy eggs", done=True)

    # Same id means same hash
    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_for_different_id() -> None:
    """Todo objects with different ids should have different hashes."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    # Different id means different hash (typically)
    assert hash(todo1) != hash(todo2)


def test_todo_in_set() -> None:
    """Todo objects can be used in sets for deduplication."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy eggs")  # Same id, different text
    todo3 = Todo(id=2, text="buy bread")

    # Set should deduplicate by id
    todo_set = {todo1, todo2, todo3}
    assert len(todo_set) == 2  # Only 2 unique ids


def test_todo_set_deduplication() -> None:
    """Multiple Todo objects with same id should collapse to single set element."""
    todos = [Todo(id=1, text="a"), Todo(id=1, text="b"), Todo(id=1, text="c")]
    todo_set = set(todos)

    # All have same id, so set should have 1 element
    assert len(todo_set) == 1


def test_todo_equality_with_none() -> None:
    """Todo should not be equal to None."""
    todo = Todo(id=1, text="task")
    assert todo != None  # noqa: E711


def test_todo_equality_with_other_type() -> None:
    """Todo should not be equal to other types."""
    todo = Todo(id=1, text="task")
    assert todo != "1"
    assert todo != 1
    assert todo != {"id": 1, "text": "task"}


def test_todo_hash_stability() -> None:
    """Todo hash should be stable across multiple calls."""
    todo = Todo(id=42, text="stable task")
    hash1 = hash(todo)
    hash2 = hash(todo)
    hash3 = hash(todo)

    assert hash1 == hash2 == hash3
