"""Tests for Todo __eq__ and __hash__ methods (Issue #6244)."""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_with_same_fields() -> None:
    """Two Todo objects with same id, text, done should compare equal."""
    todo1 = Todo(id=1, text="buy groceries", done=False)
    todo2 = Todo(id=1, text="buy groceries", done=False)
    assert todo1 == todo2


def test_todo_equality_with_different_id() -> None:
    """Two Todo objects with different ids should not be equal."""
    todo1 = Todo(id=1, text="task a", done=False)
    todo2 = Todo(id=2, text="task a", done=False)
    assert todo1 != todo2


def test_todo_equality_with_different_text() -> None:
    """Two Todo objects with different text should not be equal."""
    todo1 = Todo(id=1, text="task a", done=False)
    todo2 = Todo(id=1, text="task b", done=False)
    assert todo1 != todo2


def test_todo_equality_with_different_done() -> None:
    """Two Todo objects with different done status should not be equal."""
    todo1 = Todo(id=1, text="task a", done=False)
    todo2 = Todo(id=1, text="task a", done=True)
    assert todo1 != todo2


def test_todo_hash_allows_set_operations() -> None:
    """Todo objects should be hashable for use in sets."""
    todo1 = Todo(id=1, text="task a", done=False)
    todo2 = Todo(id=1, text="task a", done=False)
    todo_set = {todo1, todo2}
    assert len(todo_set) == 1


def test_todo_hash_with_different_ids() -> None:
    """Todo objects with different ids should not deduplicate in sets."""
    todo1 = Todo(id=1, text="task a", done=False)
    todo2 = Todo(id=2, text="task b", done=False)
    todo_set = {todo1, todo2}
    assert len(todo_set) == 2


def test_todo_not_equal_to_non_todo() -> None:
    """Todo should not be equal to non-Todo objects."""
    todo = Todo(id=1, text="task a", done=False)
    assert todo != "task a"
    assert todo != 1
    assert todo != {"id": 1, "text": "task a", "done": False}
