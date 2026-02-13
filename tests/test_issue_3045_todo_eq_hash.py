"""Tests for Todo.__eq__ and __hash__ methods (Issue #3045).

These tests verify that:
1. Todo objects with the same id are equal (__eq__)
2. Todo objects can be used in sets and as dict keys (__hash__)
3. Todo objects with different ids are not equal
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_returns_true() -> None:
    """Todo objects with the same id should be equal."""
    todo1 = Todo(id=1, text="task a")
    todo2 = Todo(id=1, text="task b")

    # Same id, different text - should still be equal
    assert todo1 == todo2


def test_todo_eq_different_id_returns_false() -> None:
    """Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text")
    todo2 = Todo(id=2, text="same text")

    # Different id, same text - should not be equal
    assert todo1 != todo2


def test_todo_eq_same_object_returns_true() -> None:
    """A Todo should be equal to itself."""
    todo = Todo(id=1, text="task")
    assert todo == todo


def test_todo_eq_different_done_status_same_id_returns_true() -> None:
    """Todo objects with same id but different done status should be equal."""
    todo1 = Todo(id=1, text="task", done=False)
    todo2 = Todo(id=1, text="task", done=True)

    assert todo1 == todo2


def test_todo_not_equal_to_non_todo() -> None:
    """A Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="task")

    # Should not be equal to other types
    assert todo != 1
    assert todo != "task"
    assert todo != {"id": 1, "text": "task"}
    assert todo != None


def test_todo_hash_based_on_id() -> None:
    """hash(Todo) should work without raising exceptions."""
    todo1 = Todo(id=1, text="task a")
    todo2 = Todo(id=1, text="task b")

    # Should not raise TypeError
    h1 = hash(todo1)
    h2 = hash(todo2)

    # Same id should produce same hash
    assert h1 == h2


def test_todo_hash_different_for_different_id() -> None:
    """hash(Todo) should be different for different ids."""
    todo1 = Todo(id=1, text="task")
    todo2 = Todo(id=2, text="task")

    # Different ids should produce different hashes (not guaranteed, but expected)
    # At minimum, both should be hashable
    h1 = hash(todo1)
    h2 = hash(todo2)

    assert isinstance(h1, int)
    assert isinstance(h2, int)


def test_todo_can_be_added_to_set() -> None:
    """Todo objects should be addable to a set."""
    todo1 = Todo(id=1, text="task a")
    todo2 = Todo(id=1, text="task b")  # Same id as todo1
    todo3 = Todo(id=2, text="task c")

    todo_set = {todo1, todo2, todo3}

    # Set should have 2 items (todo1 and todo2 are "same" due to same id)
    assert len(todo_set) == 2


def test_todo_set_deduplication() -> None:
    """Set should deduplicate Todo objects with same id."""
    todos = [
        Todo(id=1, text="first"),
        Todo(id=1, text="second"),  # Same id
        Todo(id=1, text="third"),  # Same id
        Todo(id=2, text="unique"),
    ]

    unique_todos = set(todos)
    assert len(unique_todos) == 2


def test_todo_can_be_used_as_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="key a")
    todo2 = Todo(id=1, text="key b")  # Same id as todo1
    todo3 = Todo(id=2, text="key c")

    d = {todo1: "value1", todo2: "value2", todo3: "value3"}

    # Should have 2 keys (todo1 and todo2 are "same" due to same id)
    assert len(d) == 2

    # todo2 should have overwritten todo1's value (same key)
    assert d[todo1] == "value2"
