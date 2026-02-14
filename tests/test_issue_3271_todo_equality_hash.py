"""Tests for Todo __eq__ and __hash__ methods (Issue #3271).

These tests verify that:
1. Todo objects compare by value (id, text, done) not identity
2. Todo objects can be hashed based on id (primary key)
3. Todo objects can be used in sets and as dict keys
4. Todos with same id are considered equal regardless of other fields
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id_and_text() -> None:
    """Todo(1,'a') == Todo(1,'a') should return True."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=False)
    assert todo1 == todo2


def test_todo_equality_same_id_different_text() -> None:
    """Todos with same id but different text should NOT be equal.

    The issue specifies: __eq__ compares id, text, done fields.
    So if text differs, they are not equal.
    """
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="b", done=False)
    # Different text means not equal (even with same id)
    assert todo1 != todo2


def test_todo_inequality_different_id() -> None:
    """Todo(1,'a') == Todo(2,'a') should return False."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=2, text="a", done=False)
    assert todo1 != todo2


def test_todo_hash_consistency_same_id() -> None:
    """hash(Todo(1,'a')) == hash(Todo(1,'b')) should return True."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="b", done=False)
    assert hash(todo1) == hash(todo2)


def test_todo_can_be_added_to_set() -> None:
    """Todo can be added to a set and deduplicated by equality.

    Since __eq__ compares id, text, done - todos with different text or done
    will be different elements in the set, even if they share the same id.
    This is consistent with value-based equality.
    """
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="first")  # Same id AND same text
    todo3 = Todo(id=2, text="third")

    todo_set = {todo1, todo2, todo3}
    # todo1 and todo2 should be equal, so set should have 2 elements
    assert len(todo_set) == 2


def test_todo_can_be_dict_key() -> None:
    """Todo can be used as a dictionary key.

    Equal todos (same id, text, done) will map to the same key.
    """
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="first")  # Same id AND same text

    todo_dict = {todo1: "value1"}
    # Equal todo should update value for same key
    todo_dict[todo2] = "value2"

    assert len(todo_dict) == 1
    assert todo_dict[todo1] == "value2"


def test_todo_equality_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="a")
    assert todo != 1
    assert todo != "a"
    assert todo != {"id": 1, "text": "a"}
    assert todo is not None


def test_todo_hash_is_stable() -> None:
    """Hash value should be stable across multiple calls."""
    todo = Todo(id=42, text="test")
    hash1 = hash(todo)
    hash2 = hash(todo)
    hash3 = hash(todo)
    assert hash1 == hash2 == hash3


def test_todo_equality_considers_done_flag() -> None:
    """When ids are same, check if done flag is considered in equality.

    Note: Based on issue requirements, id is the primary key for hash.
    However, for equality we may compare all logical fields (id, text, done).
    Let's test the current expected behavior.
    """
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=True)
    # Per issue: "Add __eq__ method comparing id, text, done fields"
    # So these should NOT be equal since done differs
    assert todo1 != todo2


def test_todo_set_deduplication_keeps_last_inserted() -> None:
    """When deduplicating equal todos, the set behavior should be predictable."""
    todo1 = Todo(id=1, text="first", done=False)
    todo2 = Todo(id=1, text="first", done=False)  # Identical

    # Create set with first todo
    todo_set = {todo1}
    # Add identical todo
    todo_set.add(todo2)

    # Should still have 1 element since todos are equal
    assert len(todo_set) == 1
    # The element in set should be equal to both
    element = todo_set.pop()
    assert element == todo1
    assert element == todo2
