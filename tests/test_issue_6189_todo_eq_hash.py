"""Tests for Todo.__eq__ and __hash__ methods (Issue #6189).

These tests verify that:
1. Two Todo objects with the same id are equal (== returns True)
2. Todo objects can be put into a set and deduplicated by id
3. hash(todo) == hash(todo.id) works without TypeError
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_different_text() -> None:
    """Two Todos with same id but different text should be equal."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_eq_same_id_different_done() -> None:
    """Two Todos with same id but different done status should be equal."""
    todo1 = Todo(id=1, text="task", done=False)
    todo2 = Todo(id=1, text="task", done=True)

    assert todo1 == todo2, "Todos with same id should be equal regardless of done status"


def test_todo_eq_different_id() -> None:
    """Two Todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text")
    todo2 = Todo(id=2, text="same text")

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_eq_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="task")

    assert todo != 1, "Todo should not be equal to int"
    assert todo != "1", "Todo should not be equal to string"
    assert todo != {"id": 1}, "Todo should not be equal to dict"


def test_todo_hash_consistent_with_id() -> None:
    """hash(Todo) should equal hash(todo.id)."""
    todo = Todo(id=42, text="test task")

    assert hash(todo) == hash(42), "hash(Todo) should equal hash(todo.id)"


def test_todo_hash_no_type_error() -> None:
    """hash(Todo) should not raise TypeError."""
    todo = Todo(id=1, text="task")

    # This should not raise TypeError
    hash_value = hash(todo)
    assert isinstance(hash_value, int), "hash should return an int"


def test_todo_set_deduplication() -> None:
    """Todo objects should be deduplicated in a set by id."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")  # Same id, different text
    todo3 = Todo(id=2, text="another task")

    todo_set = {todo1, todo2, todo3}

    # Should only have 2 items because todo1 and todo2 have same id
    assert len(todo_set) == 2, f"Expected 2 items, got {len(todo_set)}"


def test_todo_dict_key_usage() -> None:
    """Todo objects should work as dict keys."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")  # Same id as todo1
    todo3 = Todo(id=2, text="third")

    todo_dict = {todo1: "value1", todo2: "value2", todo3: "value3"}

    # Should only have 2 keys because todo1 and todo2 have same id
    assert len(todo_dict) == 2, f"Expected 2 keys, got {len(todo_dict)}"

    # The value for the key should be from the last assignment
    assert todo_dict[todo1] == "value2", "Dict value should be from last assignment"


def test_todo_eq_reflexive() -> None:
    """A Todo should be equal to itself."""
    todo = Todo(id=1, text="task")

    assert todo == todo, "Todo should be equal to itself"


def test_todo_eq_symmetric() -> None:
    """Equality should be symmetric: a == b implies b == a."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")

    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_eq_transitive() -> None:
    """Equality should be transitive: a == b and b == c implies a == c."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")
    todo3 = Todo(id=1, text="third")

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3
