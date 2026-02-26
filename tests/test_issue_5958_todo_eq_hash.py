"""Tests for Todo.__eq__ and __hash__ methods (Issue #5958).

These tests verify that:
1. Todo objects with the same id are considered equal
2. Todo objects with different id are not equal
3. Todo objects can be used in sets for deduplication
4. Todo objects can be used as dictionary keys
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_id_returns_true() -> None:
    """Todo objects with the same id should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2


def test_todo_eq_same_id_different_text_returns_true() -> None:
    """Todo objects with the same id should be equal regardless of text."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="different text")

    # Equality is based on id only
    assert todo1 == todo2


def test_todo_eq_same_id_different_done_returns_true() -> None:
    """Todo objects with the same id should be equal regardless of done status."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    # Equality is based on id only
    assert todo1 == todo2


def test_todo_eq_different_id_returns_false() -> None:
    """Todo objects with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy milk")

    assert todo1 != todo2


def test_todo_eq_with_non_todo_returns_false() -> None:
    """Todo compared with non-Todo should return NotImplemented (False in comparison)."""
    todo = Todo(id=1, text="buy milk")

    # Comparing with a non-Todo should not raise and should be False
    assert todo != "not a todo"
    assert todo != 1
    assert todo != {"id": 1, "text": "buy milk"}
    assert todo is not None


def test_todo_hash_same_id_same_hash() -> None:
    """Todo objects with the same id should have the same hash."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="different text")

    assert hash(todo1) == hash(todo2)


def test_todo_hash_different_id_different_hash() -> None:
    """Todo objects with different id should (likely) have different hashes."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy milk")

    # While not guaranteed, different ids should typically have different hashes
    assert hash(todo1) != hash(todo2)


def test_todo_can_be_used_in_set() -> None:
    """Todo objects should be usable in sets for deduplication."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="different text")  # Same id as todo1
    todo3 = Todo(id=2, text="buy bread")

    todo_set = {todo1, todo2, todo3}

    # Set should have 2 unique todos (by id)
    assert len(todo_set) == 2


def test_todo_set_deduplication() -> None:
    """Set should deduplicate Todo objects by id."""
    todos = [
        Todo(id=1, text="task 1"),
        Todo(id=1, text="task 1 updated"),  # Duplicate id
        Todo(id=2, text="task 2"),
        Todo(id=2, text="task 2 updated"),  # Duplicate id
        Todo(id=3, text="task 3"),
    ]

    unique_todos = set(todos)

    # Should have 3 unique todos (ids 1, 2, 3)
    assert len(unique_todos) == 3


def test_todo_can_be_used_as_dict_key() -> None:
    """Todo objects should be usable as dictionary keys."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=2, text="buy bread")

    todo_dict = {todo1: "value1", todo2: "value2"}

    assert todo_dict[todo1] == "value1"
    assert todo_dict[todo2] == "value2"


def test_todo_dict_key_lookup_by_equal_object() -> None:
    """Should be able to look up dict value using an equal Todo object."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="different text")  # Same id as todo1

    todo_dict = {todo1: "stored value"}

    # Should be able to retrieve using a different but equal Todo
    assert todo_dict[todo2] == "stored value"
