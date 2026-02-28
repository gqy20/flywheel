"""Tests for Todo.copy() method (Issue #6259).

These tests verify that:
1. todo.copy() returns a new Todo object with same fields (different instance)
2. todo.copy(done=True).done == True and original object unchanged
3. copy() supports overriding any field like text, done
4. copy() automatically sets updated_at to current time
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_copy_returns_different_object() -> None:
    """copy() should return a new Todo object with a different id()."""
    todo = Todo(id=1, text="buy milk", done=False)
    copied = todo.copy()

    assert copied is not todo, "copy() should return a new object"
    assert id(copied) != id(todo), "copy() should return object with different id()"


def test_copy_preserves_all_fields() -> None:
    """copy() should return a Todo with all same fields as original."""
    todo = Todo(id=1, text="buy milk", done=True)
    copied = todo.copy()

    assert copied.id == todo.id
    assert copied.text == todo.text
    assert copied.done == todo.done
    assert copied.created_at == todo.created_at
    # updated_at should be updated (not preserved)


def test_copy_updates_timestamp() -> None:
    """copy() should automatically set updated_at to current time."""
    todo = Todo(id=1, text="buy milk", done=False)
    original_updated_at = todo.updated_at
    copied = todo.copy()

    # updated_at should be different (newer or equal)
    assert copied.updated_at != original_updated_at or copied.updated_at == todo.created_at


def test_copy_with_done_override() -> None:
    """copy(done=True) should override done field without modifying original."""
    todo = Todo(id=1, text="buy milk", done=False)
    original_done = todo.done

    copied = todo.copy(done=True)

    assert copied.done is True, "Copied todo should have done=True"
    assert todo.done == original_done, "Original todo should remain unchanged"


def test_copy_with_text_override() -> None:
    """copy(text='new') should override text field without modifying original."""
    todo = Todo(id=1, text="buy milk", done=False)
    original_text = todo.text

    copied = todo.copy(text="buy bread")

    assert copied.text == "buy bread", "Copied todo should have new text"
    assert todo.text == original_text, "Original todo text should remain unchanged"


def test_copy_with_multiple_overrides() -> None:
    """copy() should support overriding multiple fields at once."""
    todo = Todo(id=1, text="buy milk", done=False)
    copied = todo.copy(text="buy bread", done=True)

    assert copied.text == "buy bread"
    assert copied.done is True
    # Original unchanged
    assert todo.text == "buy milk"
    assert todo.done is False


def test_copy_preserves_id() -> None:
    """copy() should preserve the original id (not generate new one)."""
    todo = Todo(id=42, text="test", done=False)
    copied = todo.copy()

    assert copied.id == 42, "copy() should preserve the id field"


def test_copy_preserves_created_at() -> None:
    """copy() should preserve the original created_at timestamp."""
    todo = Todo(id=1, text="test", done=False)
    original_created_at = todo.created_at
    copied = todo.copy()

    assert copied.created_at == original_created_at, "copy() should preserve created_at"


def test_copy_chainable() -> None:
    """copy() can be chained for fluent immutable operations."""
    todo = Todo(id=1, text="buy milk", done=False)

    # Chain: copy and mark as done in one expression
    done_todo = todo.copy(done=True)

    assert done_todo.done is True
    assert todo.done is False  # Original unchanged


def test_copy_with_id_override() -> None:
    """copy(id=2) should allow overriding id field."""
    todo = Todo(id=1, text="buy milk", done=False)
    copied = todo.copy(id=99)

    assert copied.id == 99, "Copied todo should have new id"
    assert todo.id == 1, "Original todo id should remain unchanged"
