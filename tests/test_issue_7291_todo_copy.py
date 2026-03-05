"""Tests for Todo.copy method (Issue #7291).

These tests verify that:
1. copy() returns a new Todo instance (not the same object)
2. copy() preserves text and done status
3. copy() generates new timestamps (created_at, updated_at)
4. copy(with_id=True) preserves the original id
5. copy(with_id=False) sets id=0 (default behavior)
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_todo_copy_creates_new_instance() -> None:
    """copy() should return a new Todo instance, not the same object."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy()

    # Should be different objects
    assert copied is not original
    assert id(copied) != id(original)


def test_todo_copy_preserves_content() -> None:
    """copy() should preserve text and done status from original."""
    original = Todo(id=42, text="complete task", done=True)
    copied = original.copy()

    assert copied.text == original.text
    assert copied.done == original.done


def test_todo_copy_new_timestamps() -> None:
    """copy() should generate new timestamps, not copy old ones."""
    original = Todo(id=1, text="task", done=False)
    # Small delay to ensure timestamps differ
    time.sleep(0.01)
    copied = original.copy()

    # Timestamps should be different (new ones generated)
    assert copied.created_at != original.created_at
    assert copied.updated_at != original.updated_at
    # New timestamps should be set (not empty)
    assert copied.created_at != ""
    assert copied.updated_at != ""


def test_todo_copy_with_id_false_default() -> None:
    """copy() with with_id=False (default) should set id=0."""
    original = Todo(id=99, text="task", done=False)
    copied = original.copy()

    assert copied.id == 0


def test_todo_copy_with_id_true() -> None:
    """copy(with_id=True) should preserve the original id."""
    original = Todo(id=123, text="important task", done=True)
    copied = original.copy(with_id=True)

    assert copied.id == original.id
    assert copied.id == 123


def test_todo_copy_modifications_isolated() -> None:
    """Modifying the copy should not affect the original."""
    original = Todo(id=1, text="original text", done=False)
    copied = original.copy()

    # Modify the copy
    copied.text = "modified text"
    copied.done = True

    # Original should be unchanged
    assert original.text == "original text"
    assert original.done is False


def test_todo_copy_all_fields_preserved_except_id_and_timestamps() -> None:
    """copy() should preserve all content fields except id and timestamps."""
    original = Todo(id=10, text="sample task", done=True)
    copied = original.copy(with_id=True)

    # When with_id=True, all content should match
    assert copied.id == original.id
    assert copied.text == original.text
    assert copied.done == original.done
    # Timestamps should still be new
    assert copied.created_at != original.created_at
    assert copied.updated_at != original.updated_at
