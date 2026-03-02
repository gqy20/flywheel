"""Tests for Todo.__eq__ and __hash__ methods (Issue #6692).

These tests verify that:
1. Todo objects with same id, text, done are equal
2. Todo objects with different id are not equal
3. Todo objects can be used in sets and dicts for deduplication
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_eq_same_values() -> None:
    """Two Todo objects with same id, text, done should be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert todo1 == todo2, "Todos with same values should be equal"


def test_todo_eq_different_id() -> None:
    """Two Todo objects with different id should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2, "Todos with different id should not be equal"


def test_todo_eq_different_text() -> None:
    """Two Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=False)

    assert todo1 != todo2, "Todos with different text should not be equal"


def test_todo_eq_different_done() -> None:
    """Two Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    assert todo1 != todo2, "Todos with different done status should not be equal"


def test_todo_eq_not_implemented() -> None:
    """Todo comparison with non-Todo should return NotImplemented."""
    todo = Todo(id=1, text="buy milk", done=False)

    assert todo != "not a todo"
    assert todo != 1
    assert todo != None


def test_todo_hash_based_on_id() -> None:
    """Todo objects with same id should have same hash."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=False)

    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_hash_different_id() -> None:
    """Todo objects with different id should have different hash."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    # Note: hash collision is theoretically possible but extremely unlikely
    assert hash(todo1) != hash(todo2), "Todos with different id should have different hash"


def test_todo_in_set() -> None:
    """Todo objects should be usable in a set."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy bread", done=True)
    todo3 = Todo(id=1, text="buy milk", done=False)  # Duplicate of todo1

    todo_set = {todo1, todo2, todo3}

    # Set should deduplicate based on equality
    assert len(todo_set) == 2, f"Set should have 2 unique todos, got {len(todo_set)}"


def test_todo_as_dict_key() -> None:
    """Todo objects should be usable as dict keys."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy bread", done=True)
    todo3 = Todo(id=1, text="buy milk", done=False)  # Duplicate of todo1

    todo_dict = {todo1: "first", todo2: "second", todo3: "third"}

    # Dict should deduplicate keys based on equality
    assert len(todo_dict) == 2, f"Dict should have 2 unique keys, got {len(todo_dict)}"
    assert todo_dict[todo1] == "third", "Later value should overwrite earlier for equal key"


def test_todo_set_with_different_done_status() -> None:
    """Todo objects with same id but different done status should not deduplicate."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy milk", done=True)

    todo_set = {todo1, todo2}

    # Since equality considers done, these are different objects
    assert len(todo_set) == 2, f"Set should have 2 todos with different done status, got {len(todo_set)}"
