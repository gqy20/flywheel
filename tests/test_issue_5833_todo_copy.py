"""Tests for Todo.copy method (Issue #5833).

These tests verify that:
1. copy() returns a new Todo instance with same fields
2. copy(**kwargs) allows overriding specific fields
3. Modifications to copy don't affect original
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_copy_returns_new_instance() -> None:
    """copy() should return a different Todo object."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy()

    # Should be a different object
    assert copy is not original
    # Should be a Todo instance
    assert isinstance(copy, Todo)


def test_todo_copy_preserves_all_fields() -> None:
    """copy() should preserve all fields from the original."""
    original = Todo(id=1, text="buy milk", done=True)
    copy = original.copy()

    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done
    assert copy.created_at == original.created_at
    assert copy.updated_at == original.updated_at


def test_todo_copy_overrides_text() -> None:
    """copy(text='new') should only override text field."""
    original = Todo(id=1, text="buy milk", done=True)
    copy = original.copy(text="buy bread")

    assert copy.text == "buy bread"
    assert copy.id == original.id
    assert copy.done == original.done


def test_todo_copy_overrides_id() -> None:
    """copy(id=2) should only override id field."""
    original = Todo(id=1, text="buy milk", done=True)
    copy = original.copy(id=2)

    assert copy.id == 2
    assert copy.text == original.text
    assert copy.done == original.done


def test_todo_copy_overrides_done() -> None:
    """copy(done=False) should only override done field."""
    original = Todo(id=1, text="buy milk", done=True)
    copy = original.copy(done=False)

    assert copy.done is False
    assert copy.id == original.id
    assert copy.text == original.text


def test_todo_copy_overrides_multiple_fields() -> None:
    """copy(id=2, text='new') should override multiple fields."""
    original = Todo(id=1, text="buy milk", done=True)
    copy = original.copy(id=2, text="buy bread", done=False)

    assert copy.id == 2
    assert copy.text == "buy bread"
    assert copy.done is False


def test_todo_copy_modification_does_not_affect_original() -> None:
    """Modifications to copy should not affect the original object."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy(text="buy bread")

    # Modify the copy
    copy.mark_done()

    # Original should be unchanged
    assert original.done is False
    assert original.text == "buy milk"
    assert copy.done is True
    assert copy.text == "buy bread"


def test_todo_copy_independence_of_nested_changes() -> None:
    """Changes to copy's fields should not affect original."""
    original = Todo(id=1, text="buy milk")
    copy = original.copy()

    # Modify copy
    copy.text = "changed text"
    copy.done = True

    # Original should be unchanged
    assert original.text == "buy milk"
    assert original.done is False
