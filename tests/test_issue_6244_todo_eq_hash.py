"""Tests for Todo __eq__ and __hash__ methods (Issue #6244)."""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_equality_same_id_text_done() -> None:
    """Issue #6244: Two Todo objects with same id, text, done compare equal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")

    assert todo1 == todo2


def test_todo_equality_different_ids() -> None:
    """Issue #6244: Todo objects with different ids compare unequal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="a")

    assert todo1 != todo2


def test_todo_equality_different_text() -> None:
    """Issue #6244: Todo objects with different text compare unequal."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="b")

    assert todo1 != todo2


def test_todo_equality_different_done() -> None:
    """Issue #6244: Todo objects with different done status compare unequal."""
    todo1 = Todo(id=1, text="a", done=False)
    todo2 = Todo(id=1, text="a", done=True)

    assert todo1 != todo2


def test_todo_can_be_added_to_set() -> None:
    """Issue #6244: Todo objects can be added to a set without error."""
    todo1 = Todo(id=1, text="a")
    todo_set = {todo1}

    assert len(todo_set) == 1
    assert todo1 in todo_set


def test_todo_set_deduplication() -> None:
    """Issue #6244: Set deduplicates Todo objects with same id, text, done."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")

    todo_set = {todo1, todo2}

    assert len(todo_set) == 1


def test_todo_set_keeps_different_todos() -> None:
    """Issue #6244: Set keeps Todo objects with different ids."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=2, text="b")

    todo_set = {todo1, todo2}

    assert len(todo_set) == 2


def test_todo_hash_consistency() -> None:
    """Issue #6244: Hash of same Todo should be consistent."""
    todo1 = Todo(id=1, text="a")
    todo2 = Todo(id=1, text="a")

    assert hash(todo1) == hash(todo2)
