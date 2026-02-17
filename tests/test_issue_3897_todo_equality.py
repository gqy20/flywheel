"""Tests for Todo equality and hashing (Issue #3897).

These tests verify that:
1. Todo equality is based on id field only
2. Todos with same id are equal regardless of other fields
3. Todo hash is based on id, enabling set/dict usage
4. Todo inequality works correctly for different ids
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id() -> None:
    """Todos with same id should be equal regardless of other fields."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_equality_same_id_minimal() -> None:
    """Todos with same id and different text should be equal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")

    assert todo1 == todo2, "Todos with same id should be equal even with different text"


def test_todo_inequality_different_id() -> None:
    """Todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="same text")
    todo2 = Todo(id=2, text="same text")

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_inequality_different_id_done_status() -> None:
    """Todos with different ids should not be equal even with same done status."""
    todo1 = Todo(id=1, text="task", done=True)
    todo2 = Todo(id=2, text="task", done=True)

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_hash_same_id() -> None:
    """hash(Todo) should work and be consistent with id."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")

    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_hash_different_id() -> None:
    """hash(Todo) should differ for different ids."""
    todo1 = Todo(id=1, text="same")
    todo2 = Todo(id=2, text="same")

    assert hash(todo1) != hash(todo2), "Todos with different ids should have different hashes"


def test_todo_set_deduplication() -> None:
    """Todos with same id should be deduplicated in sets."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")  # Same id, different text
    todo3 = Todo(id=2, text="third")

    unique_todos = {todo1, todo2, todo3}

    assert len(unique_todos) == 2, f"Set should have 2 unique todos, got {len(unique_todos)}"


def test_todo_dict_key() -> None:
    """Todos should be usable as dict keys based on id."""
    todo1 = Todo(id=1, text="original")
    todo2 = Todo(id=1, text="updated")  # Same id, different text

    mapping = {todo1: "value1"}
    mapping[todo2] = "value2"

    # Since todo1 == todo2, this should overwrite, not add a new key
    assert len(mapping) == 1, "Dict should have 1 key since todos are equal"
    assert mapping[todo1] == "value2", "Value should be updated"


def test_todo_equality_reflexive() -> None:
    """A Todo should be equal to itself."""
    todo = Todo(id=1, text="task")
    assert todo == todo, "Todo should be equal to itself"


def test_todo_equality_symmetric() -> None:
    """Equality should be symmetric: if a == b then b == a."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")

    assert todo1 == todo2
    assert todo2 == todo1, "Equality should be symmetric"


def test_todo_equality_transitive() -> None:
    """Equality should be transitive: if a == b and b == c then a == c."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")
    todo3 = Todo(id=1, text="third")

    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3, "Equality should be transitive"


def test_todo_not_equal_to_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="task")

    assert todo != 1, "Todo should not equal int"
    assert todo != "task", "Todo should not equal string"
    assert todo != {"id": 1, "text": "task"}, "Todo should not equal dict"
    assert todo is not None, "Todo should not equal None"
