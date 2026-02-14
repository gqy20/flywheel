"""Tests for Todo __eq__ and __hash__ methods (Issue #3271).

These tests verify that Todo objects support value-based comparison
and can be used in sets or as dict keys.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id_same_text() -> None:
    """Two Todo objects with same id and text should be equal.

    Note: We need to control timestamps to ensure equality test works,
    or we compare Todos with explicit timestamps.
    """
    # Use explicit timestamps to ensure equality
    todo1 = Todo(id=1, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    todo2 = Todo(id=1, text="a", done=False, created_at="2024-01-01", updated_at="2024-01-01")
    assert todo1 == todo2


def test_todo_equality_same_id_different_text() -> None:
    """Two Todo objects with same id but different text should NOT be equal.

    The equality is based on all fields (id, text, done), not just id.
    """
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    # Different text means not equal
    assert todo1 != todo2


def test_todo_equality_different_id() -> None:
    """Two Todo objects with different ids should NOT be equal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")
    assert todo1 != todo2


def test_todo_equality_same_id_different_done() -> None:
    """Two Todo objects with same id but different done status should NOT be equal."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=True)
    assert todo1 != todo2


def test_todo_hash_consistency_same_id() -> None:
    """Hash should be based on id only, allowing deduplication by id in sets."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    # Same id means same hash
    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_for_different_ids() -> None:
    """Hash should differ for different ids."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")
    assert hash(todo1) != hash(todo2)


def test_todo_can_be_added_to_set() -> None:
    """Todo objects should be usable in sets."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="b")
    todo_set = {todo1, todo2}
    assert len(todo_set) == 2
    assert todo1 in todo_set
    assert todo2 in todo_set


def test_todo_set_deduplication_by_id() -> None:
    """Set should deduplicate Todo objects by id (via hash).

    Note: Since Todo(1,'a') != Todo(1,'b') but they have the same hash,
    both will be kept in the set (hash collision with unequal objects).
    This is expected behavior - hash based on id for dict key usability,
    but equality checks all fields for proper comparison.
    """
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")  # Same id, different text
    todo3 = Todo(id=1, text="a")  # Same as todo1
    todo_set = {todo1, todo2, todo3}
    # todo1 and todo2 are kept (same hash but not equal)
    # todo3 is equal to todo1 so it's deduplicated
    assert len(todo_set) == 2


def test_todo_can_be_dict_key() -> None:
    """Todo objects should be usable as dict keys."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="b")
    todo_dict = {todo1: "first", todo2: "second"}
    assert todo_dict[todo1] == "first"
    assert todo_dict[todo2] == "second"


def test_todo_not_equal_to_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="a")
    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "a"}
    assert todo != None
