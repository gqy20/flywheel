"""Tests for Todo.__hash__ method (Issue #4588).

These tests verify that:
1. hash(Todo) returns a consistent integer
2. Todo objects can be added to a set
3. Todo with same id hashes to same value (deduplication)
4. Todo objects can be used as dict keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_hash_returns_int() -> None:
    """hash(Todo) should return an integer."""
    todo = Todo(id=1, text="buy milk")
    result = hash(todo)

    assert isinstance(result, int)


def test_todo_hash_consistent_for_same_id() -> None:
    """Todo with same id should hash to same value."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="different text")

    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_for_different_ids() -> None:
    """Todo with different ids should hash to different values."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy milk")

    # While not guaranteed, id-based hashing typically produces different hashes
    assert hash(todo1) != hash(todo2)


def test_todo_can_be_added_to_set() -> None:
    """Todo objects should be addable to a set."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy bread")

    todo_set = {todo1, todo2}

    assert len(todo_set) == 2
    assert todo1 in todo_set
    assert todo2 in todo_set


def test_todo_set_deduplication_by_id() -> None:
    """Set should deduplicate Todo objects with same id."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy milk")

    todo_set = {todo1, todo2}

    assert len(todo_set) == 1


def test_todo_set_deduplication_different_text_same_id() -> None:
    """Set should deduplicate Todo with same id even if text differs."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="different text")
    todo3 = Todo(id=1, text="yet another text")

    todo_set = {todo1, todo2, todo3}

    # All have same id, should dedupe to 1
    assert len(todo_set) == 1


def test_todo_can_be_used_as_dict_key() -> None:
    """Todo objects should be usable as dict keys."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy bread")

    todo_dict = {todo1: "first", todo2: "second"}

    assert todo_dict[todo1] == "first"
    assert todo_dict[todo2] == "second"
    assert len(todo_dict) == 2


def test_todo_dict_key_deduplication_by_id() -> None:
    """Dict should deduplicate Todo keys with same id."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="different text")

    todo_dict = {todo1: "first", todo2: "second"}

    # Same id should result in one key, last value wins
    assert len(todo_dict) == 1
    assert todo_dict[todo1] == "second"
