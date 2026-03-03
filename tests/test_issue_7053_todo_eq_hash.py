"""Tests for Todo.__eq__ and __hash__ methods (Issue #7053).

These tests verify that:
1. Two Todo objects with same id are equal regardless of other fields
2. Todo can be added to a set without error
3. Hash is based on id field only
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_equal() -> None:
    """Todo(1, 'a') == Todo(1, 'b') should return True (same id)."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_eq_different_id_not_equal() -> None:
    """Todo(1, 'a') != Todo(2, 'a') should return True (different id)."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")

    assert todo1 != todo2, "Todos with different id should not be equal"


def test_todo_eq_same_id_different_done_equal() -> None:
    """Todos with same id but different done status should be equal."""
    todo1 = Todo(id=1, text="task", done=False)
    todo2 = Todo(id=1, text="task", done=True)

    assert todo1 == todo2, "Todos with same id should be equal regardless of done status"


def test_todo_hash_same_id_same_hash() -> None:
    """Todos with same id should have the same hash."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")

    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_hash_different_id_different_hash() -> None:
    """Todos with different id should have different hashes."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")

    assert hash(todo1) != hash(todo2), "Todos with different id should have different hashes"


def test_todo_set_deduplication() -> None:
    """len({Todo(1, 'a'), Todo(1, 'b')}) should be 1 (set deduplication by id)."""
    todo_set = {Todo(id=1, text="a"), Todo(id=1, text="b")}

    assert len(todo_set) == 1, "Set should deduplicate todos with same id"


def test_todo_set_multiple_ids() -> None:
    """Set should keep todos with different ids."""
    todo_set = {
        Todo(id=1, text="a"),
        Todo(id=2, text="b"),
        Todo(id=3, text="c"),
    }

    assert len(todo_set) == 3, "Set should keep todos with different ids"


def test_todo_set_with_duplicate_ids() -> None:
    """Set should deduplicate based on id only."""
    todo_set = {
        Todo(id=1, text="a", done=False),
        Todo(id=1, text="b", done=True),
        Todo(id=2, text="c", done=False),
    }

    assert len(todo_set) == 2, "Set should have 2 unique todos (by id)"


def test_todo_eq_with_non_todo() -> None:
    """Todo comparison with non-Todo should return False."""
    todo = Todo(id=1, text="a")

    assert todo != 1, "Todo should not equal an integer"
    assert todo != "Todo", "Todo should not equal a string"
    assert todo != {"id": 1, "text": "a"}, "Todo should not equal a dict"


def test_todo_hash_consistency() -> None:
    """Hash should remain consistent across the lifetime of the object."""
    todo = Todo(id=42, text="original")
    original_hash = hash(todo)

    # Modify mutable fields
    todo.mark_done()
    todo.rename("new text")

    # Hash should remain the same (based on id only)
    assert hash(todo) == original_hash, "Hash should not change when other fields change"
