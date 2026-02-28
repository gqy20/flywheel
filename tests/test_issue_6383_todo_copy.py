"""Tests for Todo.copy() method (Issue #6383).

These tests verify that:
1. copy() returns a new Todo object with the same values
2. copy(**overrides) allows modifying specific fields
3. Timestamps (created_at/updated_at) are preserved unless explicitly overridden
4. copy() supports immutable-style programming patterns
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_copy_returns_new_object() -> None:
    """copy() should return a new Todo object with different identity."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy()

    assert copied is not original, "copy() should return a new object"
    assert id(copied) != id(original), "copy() should have different identity"


def test_todo_copy_preserves_all_fields() -> None:
    """copy() should preserve all fields from the original Todo."""
    original = Todo(id=1, text="buy milk", done=True)
    copied = original.copy()

    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done
    assert copied.created_at == original.created_at
    assert copied.updated_at == original.updated_at


def test_todo_copy_with_text_override() -> None:
    """copy(text='new') should return a copy with modified text only."""
    original = Todo(id=1, text="buy milk", done=True)
    copied = original.copy(text="buy bread")

    assert copied.text == "buy bread"
    assert copied.id == original.id
    assert copied.done == original.done
    assert copied.created_at == original.created_at
    assert copied.updated_at == original.updated_at


def test_todo_copy_with_done_override() -> None:
    """copy(done=True) should return a copy with modified done status only."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(done=True)

    assert copied.done is True
    assert copied.text == original.text
    assert copied.id == original.id
    assert copied.created_at == original.created_at
    assert copied.updated_at == original.updated_at


def test_todo_copy_preserves_timestamps() -> None:
    """copy() should preserve created_at/updated_at unless explicitly overridden."""
    original = Todo(id=1, text="buy milk", done=False)
    original_created = original.created_at
    original_updated = original.updated_at

    # copy() without overrides should preserve timestamps
    copied = original.copy()
    assert copied.created_at == original_created
    assert copied.updated_at == original_updated


def test_todo_copy_with_multiple_overrides() -> None:
    """copy() should handle multiple overrides at once."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(text="buy bread", done=True)

    assert copied.text == "buy bread"
    assert copied.done is True
    assert copied.id == original.id
    assert copied.created_at == original.created_at
    assert copied.updated_at == original.updated_at


def test_todo_copy_with_id_override() -> None:
    """copy(id=2) should allow changing the id field."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy(id=2)

    assert copied.id == 2
    assert copied.text == original.text
    assert copied.done == original.done


def test_todo_copy_supports_immutability_pattern() -> None:
    """copy() enables immutable-style updates without modifying original."""
    original = Todo(id=1, text="original", done=False)
    original_updated_at = original.updated_at

    # Immutable-style update: create new version instead of modifying
    completed = original.copy(done=True)
    renamed = completed.copy(text="renamed")

    # Original should be unchanged
    assert original.done is False
    assert original.text == "original"
    assert original.updated_at == original_updated_at

    # Completed should have done=True but original text
    assert completed.done is True
    assert completed.text == "original"

    # Renamed should have both changes
    assert renamed.done is True
    assert renamed.text == "renamed"
