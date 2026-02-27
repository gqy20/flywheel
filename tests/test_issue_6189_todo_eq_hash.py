"""Tests for Todo.__eq__ and __hash__ methods (Issue #6189).

These tests verify that:
1. Two Todo objects with the same id are equal (== returns True)
2. Todo objects can be placed in a set and deduplicated by id
3. hash(todo) == hash(todo.id) and does not raise TypeError
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_equal() -> None:
    """Two Todo objects with the same id should be equal regardless of other fields."""
    todo1 = Todo(id=1, text="task a", done=False)
    todo2 = Todo(id=1, text="task b", done=True)

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_eq_different_id_not_equal() -> None:
    """Two Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text", done=False)
    todo2 = Todo(id=2, text="same text", done=False)

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_eq_none_not_equal() -> None:
    """Todo should not be equal to None or other types."""
    todo = Todo(id=1, text="task")

    assert todo != None  # noqa: E711
    assert todo != "not a todo"
    assert todo != 1


def test_todo_hash_same_as_id_hash() -> None:
    """hash(todo) should equal hash(todo.id)."""
    todo = Todo(id=42, text="some task")

    assert hash(todo) == hash(42)


def test_todo_hash_no_type_error() -> None:
    """hash(todo) should not raise TypeError."""
    todo = Todo(id=1, text="task")

    # This should not raise TypeError
    h = hash(todo)
    assert isinstance(h, int)


def test_todo_set_deduplication() -> None:
    """Todo objects should be deduplicated by id in a set."""
    todo1 = Todo(id=1, text="task a", done=False)
    todo2 = Todo(id=1, text="task b", done=True)  # Same id, different content
    todo3 = Todo(id=2, text="task c", done=False)

    todo_set = {todo1, todo2, todo3}

    assert len(todo_set) == 2, f"Set should have 2 unique todos by id, got {len(todo_set)}"


def test_todo_dict_key() -> None:
    """Todo objects should be usable as dict keys."""
    todo1 = Todo(id=1, text="original")
    todo2 = Todo(id=1, text="duplicate")  # Same id

    d = {todo1: "value1"}

    # todo2 should be considered the same key as todo1
    assert d[todo2] == "value1"


def test_todo_eq_reflexive() -> None:
    """A Todo should be equal to itself."""
    todo = Todo(id=1, text="task")

    assert todo == todo


def test_todo_eq_symmetric() -> None:
    """Equality should be symmetric: a == b implies b == a."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")

    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_eq_transitive() -> None:
    """Equality should be transitive: a == b and b == c implies a == c."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    todo3 = Todo(id=1, text="c")

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3
