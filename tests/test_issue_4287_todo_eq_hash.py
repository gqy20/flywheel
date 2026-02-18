"""Tests for Todo.__eq__ and __hash__ methods (Issue #4287).

These tests verify that:
1. Todo objects with the same id are equal (regardless of other fields)
2. Todo objects with different ids are not equal
3. Todo objects can be used in sets for deduplication
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_different_text() -> None:
    """Todo objects with same id should be equal regardless of text."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")

    assert todo1 == todo2


def test_todo_eq_same_id_different_done() -> None:
    """Todo objects with same id should be equal regardless of done status."""
    todo1 = Todo(id=1, text="task", done=False)
    todo2 = Todo(id=1, text="different task", done=True)

    assert todo1 == todo2


def test_todo_eq_different_id_same_text() -> None:
    """Todo objects with different ids should not be equal even with same text."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy milk")

    assert todo1 != todo2


def test_todo_eq_reflexive() -> None:
    """A Todo should equal itself."""
    todo = Todo(id=1, text="task")
    assert todo == todo


def test_todo_eq_symmetric() -> None:
    """Equality should be symmetric: if a == b then b == a."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=1, text="task two")

    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_eq_transitive() -> None:
    """Equality should be transitive: if a == b and b == c then a == c."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=1, text="task two")
    todo3 = Todo(id=1, text="task three")

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3


def test_todo_eq_not_equal_to_other_types() -> None:
    """Todo should not be equal to objects of other types."""
    todo = Todo(id=1, text="task")

    assert todo != "task"
    assert todo != 1
    assert todo != {"id": 1, "text": "task"}
    assert todo is not None


def test_todo_hash_consistent_with_eq() -> None:
    """Equal Todo objects should have the same hash."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")

    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_for_different_ids() -> None:
    """Todo objects with different ids should have different hashes (not required but expected)."""
    todo1 = Todo(id=1, text="task")
    todo2 = Todo(id=2, text="task")

    # Different ids typically produce different hashes
    # (not guaranteed but expected for good hash function)
    # At minimum, they should both be hashable
    h1 = hash(todo1)
    h2 = hash(todo2)
    assert isinstance(h1, int)
    assert isinstance(h2, int)


def test_todo_set_deduplication() -> None:
    """Todo objects should be deduplicated in sets based on id."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")  # Same id, different text
    todo3 = Todo(id=2, text="buy eggs")

    todo_set = {todo1, todo2, todo3}

    # Should have only 2 unique todos (by id)
    assert len(todo_set) == 2


def test_todo_set_add_same_id() -> None:
    """Adding a Todo with same id to a set should not increase size."""
    todo1 = Todo(id=1, text="original")
    todo2 = Todo(id=1, text="updated")

    todo_set = {todo1}
    todo_set.add(todo2)

    assert len(todo_set) == 1


def test_todo_in_set() -> None:
    """Todo objects should be findable in sets by id."""
    todo1 = Todo(id=1, text="task")
    todo2 = Todo(id=1, text="different task with same id")

    todo_set = {todo1}

    assert todo2 in todo_set


def test_todo_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="original")
    todo2 = Todo(id=1, text="updated")

    d = {todo1: "value1"}
    d[todo2] = "value2"

    # Should have only 1 key since todo1 == todo2
    assert len(d) == 1
    # The value should be updated
    assert d[todo1] == "value2"
