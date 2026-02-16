"""Tests for Todo equality and comparison operators (Issue #3679)."""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id() -> None:
    """Two Todo objects with the same id should be equal."""
    todo_a = Todo(id=1, text="task a")
    todo_b = Todo(id=1, text="task b")

    assert todo_a == todo_b


def test_todo_inequality_different_id() -> None:
    """Two Todo objects with different ids should not be equal."""
    todo_a = Todo(id=1, text="same text")
    todo_b = Todo(id=2, text="same text")

    assert todo_a != todo_b


def test_todo_equality_with_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="task")

    assert todo != 1
    assert todo != "1"
    assert todo != {"id": 1, "text": "task"}
    assert todo is not None


def test_todo_sort_by_created_at() -> None:
    """Todos should be sortable by created_at in ascending order."""
    import time

    todo_a = Todo(id=1, text="first")
    time.sleep(0.01)  # Ensure different timestamps
    todo_b = Todo(id=2, text="second")
    time.sleep(0.01)
    todo_c = Todo(id=3, text="third")

    # Sort in reverse order of creation
    todos = [todo_c, todo_a, todo_b]
    sorted_todos = sorted(todos)

    assert sorted_todos[0].id == 1
    assert sorted_todos[1].id == 2
    assert sorted_todos[2].id == 3


def test_todo_less_than_based_on_created_at() -> None:
    """__lt__ should compare based on created_at."""
    import time

    todo_a = Todo(id=1, text="first")
    time.sleep(0.01)
    todo_b = Todo(id=2, text="second")

    assert todo_a < todo_b
    assert not todo_b < todo_a


def test_todo_hash_consistency() -> None:
    """Hash should be consistent with equality (based on id)."""
    todo_a = Todo(id=1, text="task a")
    todo_b = Todo(id=1, text="task b")

    # Equal objects should have the same hash
    assert hash(todo_a) == hash(todo_b)

    # Should be usable in sets
    todo_set = {todo_a, todo_b}
    assert len(todo_set) == 1
