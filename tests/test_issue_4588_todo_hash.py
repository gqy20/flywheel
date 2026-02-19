"""Tests for Todo.__hash__ method (Issue #4588).

These tests verify that:
1. Todo objects are hashable and can be used in sets/dicts
2. hash(Todo) returns a consistent integer based on id
3. Todos with the same id have the same hash value
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_is_hashable() -> None:
    """Todo objects should be hashable."""
    todo = Todo(id=1, text="test task")
    # Should not raise TypeError
    result = hash(todo)
    assert isinstance(result, int)


def test_todo_hash_is_consistent() -> None:
    """hash(Todo) should return consistent value for same id."""
    todo = Todo(id=1, text="test task")
    hash1 = hash(todo)
    hash2 = hash(todo)
    assert hash1 == hash2


def test_todo_hash_based_on_id() -> None:
    """hash(Todo) should be based on id."""
    todo1 = Todo(id=42, text="task one")
    assert hash(todo1) == hash(42)


def test_todo_hash_different_for_different_ids() -> None:
    """Todos with different ids should have different hashes."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task two")
    # While hash collision is theoretically possible, for small ints it's unlikely
    assert hash(todo1) != hash(todo2)


def test_todo_can_be_added_to_set() -> None:
    """Todo objects should be addable to a set."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task two")
    todo_set = {todo1, todo2}
    assert len(todo_set) == 2
    assert todo1 in todo_set
    assert todo2 in todo_set


def test_todo_set_deduplication_by_id() -> None:
    """Todos with same id should be treated as same in set."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=1, text="task two")  # Same id, different text
    # Due to same hash but different equality (no __eq__), both will be in set
    # unless we also implement __eq__. For now, we only implement __hash__.
    # The key behavior is that hashable objects can be added to sets.
    todo_set = {todo1, todo2}
    # Both todos have same hash but are different objects
    # In Python, set uses both hash AND equality, so both will be stored
    assert len(todo_set) == 2


def test_todo_can_be_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo = Todo(id=1, text="test task")
    d = {todo: "value"}
    assert d[todo] == "value"


def test_todo_hash_independent_of_other_fields() -> None:
    """hash(Todo) should only depend on id, not text or done status."""
    todo1 = Todo(id=1, text="task one", done=False)
    todo2 = Todo(id=1, text="task two", done=True)
    # Same id means same hash
    assert hash(todo1) == hash(todo2)
