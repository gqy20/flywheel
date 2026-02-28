"""Tests for Todo.copy method (Issue #6259).

These tests verify that:
1. copy() returns a new Todo instance with the same field values
2. copy() returns a different object (different id())
3. Modifying the copy does not affect the original
4. copy(**overrides) allows overriding any field
5. copy() automatically sets updated_at to current time
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_copy_returns_new_instance() -> None:
    """copy() should return a new Todo instance (different id())."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy()

    assert copy is not original
    assert id(copy) != id(original)


def test_todo_copy_preserves_fields() -> None:
    """copy() should preserve all field values from original."""
    original = Todo(id=1, text="buy milk", done=True)
    copy = original.copy()

    assert copy.id == original.id
    assert copy.text == original.text
    assert copy.done == original.done


def test_todo_copy_isolation() -> None:
    """Modifying the copy should not affect the original."""
    original = Todo(id=1, text="original text", done=False)
    copy = original.copy()

    # Modify the copy using existing mutation methods
    copy.mark_done()

    # Original should remain unchanged
    assert original.done is False
    assert copy.done is True


def test_todo_copy_with_done_override() -> None:
    """copy(done=True) should set done=True in the copy."""
    original = Todo(id=1, text="task", done=False)
    copy = original.copy(done=True)

    assert copy.done is True
    assert original.done is False  # original unchanged


def test_todo_copy_with_text_override() -> None:
    """copy(text='new') should set text in the copy."""
    original = Todo(id=1, text="old text", done=False)
    copy = original.copy(text="new text")

    assert copy.text == "new text"
    assert original.text == "old text"  # original unchanged


def test_todo_copy_with_multiple_overrides() -> None:
    """copy() should support overriding multiple fields at once."""
    original = Todo(id=1, text="original", done=False)
    copy = original.copy(text="modified", done=True)

    assert copy.text == "modified"
    assert copy.done is True
    assert original.text == "original"
    assert original.done is False


def test_todo_copy_updates_timestamp() -> None:
    """copy() should set updated_at to current time."""
    import time

    original = Todo(id=1, text="task")
    original_updated_at = original.updated_at

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    copy = original.copy()

    # Copy should have a newer updated_at
    assert copy.updated_at != original_updated_at
    # Original should remain unchanged
    assert original.updated_at == original_updated_at
