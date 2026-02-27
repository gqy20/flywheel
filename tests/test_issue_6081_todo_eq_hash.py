"""Tests for Todo.__eq__ and __hash__ methods (Issue #6081).

These tests verify that:
1. Two Todo objects with same id are equal regardless of other fields
2. Todo objects can be used in sets (hashable)
3. Todo objects can be used as dict keys
4. Hash is stable across field mutations (except id)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_by_id_only() -> None:
    """Two Todo objects with same id should be equal regardless of other fields."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=1, text="buy bread", done=True)

    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_inequality_by_different_id() -> None:
    """Two Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="buy milk", done=False)
    todo2 = Todo(id=2, text="buy milk", done=False)

    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_equality_after_state_change() -> None:
    """Todo equality should persist after mark_done/mark_undone."""
    todo1 = Todo(id=1, text="task")
    todo2 = Todo(id=1, text="task")

    todo1.mark_done()

    assert todo1 == todo2, "Equality should be based on id, not state"


def test_todo_hashable_in_set() -> None:
    """Todo objects should be hashable and usable in sets."""
    todo1 = Todo(id=1, text="buy milk")
    todo2 = Todo(id=1, text="buy bread")
    todo3 = Todo(id=2, text="buy eggs")

    todo_set = {todo1, todo2, todo3}

    assert len(todo_set) == 2, "Set should deduplicate by id"


def test_todo_hashable_as_dict_key() -> None:
    """Todo objects should be usable as dict keys."""
    todo = Todo(id=1, text="task")
    mapping = {todo: "value"}

    assert mapping[todo] == "value"

    # Same id, different instance should access same value
    todo2 = Todo(id=1, text="different text")
    assert mapping[todo2] == "value", "Equal todos should access same dict entry"


def test_todo_hash_stability() -> None:
    """Hash should remain stable across field mutations."""
    todo = Todo(id=1, text="original")
    original_hash = hash(todo)

    todo.mark_done()
    assert hash(todo) == original_hash, "Hash should not change after mark_done"

    todo.rename("new text")
    assert hash(todo) == original_hash, "Hash should not change after rename"


def test_todo_not_equal_to_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="task")

    assert todo != 1
    assert todo != "task"
    assert todo != {"id": 1, "text": "task"}
    assert todo is not None
