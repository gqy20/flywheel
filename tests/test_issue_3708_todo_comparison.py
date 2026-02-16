"""Tests for Todo comparison and hashing (Issue #3708).

These tests verify that:
1. Todo objects with same id/text are equal (__eq__)
2. Todo objects can be sorted by id (__lt__)
3. Todo objects are hashable for set/dict operations (__hash__)
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id() -> None:
    """Todo(id=1) == Todo(id=1) should return True."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=1, text="task one")

    assert todo1 == todo2


def test_todo_equality_different_id() -> None:
    """Todos with different ids should not be equal."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task one")

    assert todo1 != todo2


def test_todo_equality_same_id_different_text() -> None:
    """Todos with same id but different text should not be equal."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=1, text="task two")

    # Since id is the primary identifier, same id = same todo
    # But for data integrity, we compare both id and text
    assert todo1 != todo2


def test_todo_ordering_by_id() -> None:
    """sorted([Todo(id=2,...), Todo(id=1,...)]) should sort by id."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")
    todo3 = Todo(id=3, text="third")

    todos = [todo2, todo3, todo1]
    sorted_todos = sorted(todos)

    assert sorted_todos[0].id == 1
    assert sorted_todos[1].id == 2
    assert sorted_todos[2].id == 3


def test_todo_ordering_less_than() -> None:
    """Todo(id=1) < Todo(id=2) should return True."""
    todo1 = Todo(id=1, text="first")
    todo2 = Todo(id=2, text="second")

    assert todo1 < todo2
    assert not todo2 < todo1


def test_todo_hash_consistent() -> None:
    """hash(Todo) should be consistent for same content."""
    todo1 = Todo(id=1, text="task")
    todo2 = Todo(id=1, text="task")

    assert hash(todo1) == hash(todo2)


def test_todo_hash_usable_in_set() -> None:
    """Todo objects should be usable in sets."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task two")
    todo3 = Todo(id=1, text="task one")  # Duplicate of todo1

    todo_set = {todo1, todo2, todo3}

    # Set should deduplicate based on equality
    assert len(todo_set) == 2


def test_todo_hash_usable_as_dict_key() -> None:
    """Todo objects should be usable as dict keys."""
    todo1 = Todo(id=1, text="task one")
    todo2 = Todo(id=2, text="task two")

    mapping = {todo1: "first", todo2: "second"}

    assert mapping[todo1] == "first"
    assert mapping[todo2] == "second"


def test_todo_ordering_with_same_id_uses_text() -> None:
    """When ids are equal, ordering should fall back to text for stability."""
    todo1 = Todo(id=1, text="alpha")
    todo2 = Todo(id=1, text="beta")

    sorted_todos = sorted([todo2, todo1])

    assert sorted_todos[0].text == "alpha"
    assert sorted_todos[1].text == "beta"
