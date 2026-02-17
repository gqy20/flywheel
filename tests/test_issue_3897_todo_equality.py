"""Tests for Todo equality comparison based on id (Issue #3897).

These tests verify that:
1. Todo objects compare equal when they have the same id, regardless of other fields
2. Todo objects compare unequal when they have different ids
3. Todo objects are hashable and can be used in sets/dicts for deduplication
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id() -> None:
    """Todo(id=1, text='a') == Todo(id=1, text='b') should return True (same id)."""
    todo1 = Todo(id=1, text="task a", done=False)
    todo2 = Todo(id=1, text="task b", done=True)
    assert todo1 == todo2, "Todos with same id should be equal"


def test_todo_inequality_different_id() -> None:
    """Todo(id=1) != Todo(id=2) should return True."""
    todo1 = Todo(id=1, text="same text")
    todo2 = Todo(id=2, text="same text")
    assert todo1 != todo2, "Todos with different ids should not be equal"


def test_todo_equality_with_different_done_status() -> None:
    """Todos with same id but different done status should be equal."""
    todo1 = Todo(id=1, text="task", done=False)
    todo2 = Todo(id=1, text="task", done=True)
    assert todo1 == todo2, "Todos with same id should be equal regardless of done status"


def test_todo_equality_with_different_text() -> None:
    """Todos with same id but different text should be equal."""
    todo1 = Todo(id=1, text="original text")
    todo2 = Todo(id=1, text="modified text")
    assert todo1 == todo2, "Todos with same id should be equal regardless of text"


def test_todo_hash_consistency() -> None:
    """hash(Todo) should be consistent for same id."""
    todo1 = Todo(id=1, text="task a")
    todo2 = Todo(id=1, text="task b")
    assert hash(todo1) == hash(todo2), "Todos with same id should have same hash"


def test_todo_hashability() -> None:
    """Todo objects should be hashable."""
    todo = Todo(id=1, text="task")
    # This should not raise TypeError
    hash_value = hash(todo)
    assert isinstance(hash_value, int)


def test_todo_set_deduplication() -> None:
    """len({Todo(id=1), Todo(id=1)}) == 1 - sets should deduplicate by id."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")
    todo_set = {todo1, todo2}
    assert len(todo_set) == 1, "Set should deduplicate todos with same id"


def test_todo_dict_key() -> None:
    """Todo objects should work as dict keys."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=1, text="second")
    d = {todo1: "value1"}
    d[todo2] = "value2"
    # Since they're equal, there should only be one key
    assert len(d) == 1, "Dict should deduplicate keys by id"
    assert d[todo1] == "value2", "Later value should overwrite earlier"


def test_todo_reflexivity() -> None:
    """A todo should equal itself (reflexivity)."""
    todo = Todo(id=1, text="task")
    assert todo == todo, "Todo should equal itself"


def test_todo_symmetry() -> None:
    """If todo1 == todo2 then todo2 == todo1 (symmetry)."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    assert todo1 == todo2
    assert todo2 == todo1


def test_todo_transitivity() -> None:
    """If todo1 == todo2 and todo2 == todo3, then todo1 == todo3 (transitivity)."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")
    todo3 = Todo(id=1, text="c")
    assert todo1 == todo2
    assert todo2 == todo3
    assert todo1 == todo3


def test_todo_not_equal_to_non_todo() -> None:
    """Todo should not equal a non-Todo object."""
    todo = Todo(id=1, text="task")
    assert todo != 1
    assert todo != "1"
    assert todo != {"id": 1, "text": "task"}
