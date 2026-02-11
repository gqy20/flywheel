"""Tests for Todo.__eq__ and __hash__ methods (Issue #2730).

These tests verify that:
1. Todo objects can be compared by id
2. Todo objects can be used in sets
3. Todo objects can be used as dict keys
4. Equality is based on id only
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id() -> None:
    """Two Todo objects with same id should be equal."""
    todo1 = Todo(id=1, text="task one", done=False)
    todo2 = Todo(id=1, text="different text", done=True)

    # Same id should mean equal, regardless of other fields
    assert todo1 == todo2


def test_todo_eq_different_id() -> None:
    """Two Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text", done=False)
    todo2 = Todo(id=2, text="same text", done=False)

    # Different ids should not be equal
    assert todo1 != todo2


def test_todo_eq_with_other_types() -> None:
    """Todo should not equal non-Todo objects."""
    todo = Todo(id=1, text="task", done=False)

    # Should not equal other types
    assert todo != 1
    assert todo != "1"
    assert todo != {"id": 1}
    assert todo is not None


def test_todo_hash_consistent() -> None:
    """hash should be based on id and consistent."""
    todo1 = Todo(id=42, text="any text", done=False)
    todo2 = Todo(id=42, text="different text", done=True)

    # Same id should produce same hash
    assert hash(todo1) == hash(todo2)

    # Hash should be consistent across multiple calls
    assert hash(todo1) == hash(todo1)


def test_todo_hash_in_set() -> None:
    """Todo should work in a set (deduplication by id)."""
    todo1 = Todo(id=1, text="task one", done=False)
    todo2 = Todo(id=1, text="task one duplicate", done=True)  # same id
    todo3 = Todo(id=2, text="task two", done=False)

    todo_set = {todo1, todo2, todo3}

    # Set should deduplicate by id
    # todo1 and todo2 have same id, so set should have 2 items
    assert len(todo_set) == 2

    # Both todos with id=1 should be "in" the set
    assert todo1 in todo_set
    assert todo2 in todo_set
    assert todo3 in todo_set


def test_todo_as_dict_key() -> None:
    """Todo should be usable as a dictionary key."""
    todo1 = Todo(id=1, text="key one", done=False)
    todo2 = Todo(id=2, text="key two", done=True)

    todo_dict = {todo1: "value1", todo2: "value2"}

    # Should be able to retrieve by todo objects
    assert todo_dict[todo1] == "value1"
    assert todo_dict[todo2] == "value2"

    # Same id todo should work as key (even if different object)
    todo1_dup = Todo(id=1, text="different", done=True)
    assert todo_dict[todo1_dup] == "value1"


def test_todo_eq_id_only() -> None:
    """Equality should be based on id only, not other fields."""
    # Same id, different everything else
    todo1 = Todo(id=5, text="original", done=False)
    todo2 = Todo(id=5, text="modified", done=True)

    # Should still be equal
    assert todo1 == todo2

    # Should hash to same value
    assert hash(todo1) == hash(todo2)


def test_todo_in_list() -> None:
    """Todo should be findable in a list using 'in' operator."""
    todo1 = Todo(id=1, text="find me", done=False)
    todo2 = Todo(id=2, text="other", done=True)
    todo3 = Todo(id=3, text="another", done=False)

    todo_list = [todo1, todo2, todo3]

    # Should find exact todo
    assert todo1 in todo_list

    # Should find todo with same id (even if different object)
    todo1_dup = Todo(id=1, text="different text", done=True)
    assert todo1_dup in todo_list

    # Should not find todo with different id
    todo4 = Todo(id=4, text="not in list", done=False)
    assert todo4 not in todo_list
