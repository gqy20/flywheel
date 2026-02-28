"""Tests for Todo.copy() method (Issue #6341).

These tests verify that:
1. copy() returns a new Todo instance with same text/done
2. The new instance has fresh timestamps (created_at/updated_at)
3. An optional id parameter can be passed to set a new id
4. Modifying the original does not affect the copy
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_todo_copy_returns_different_instance() -> None:
    """copy() should return a new Todo instance (not the same object)."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy()

    assert copy is not original, "copy() should return a new instance"
    assert isinstance(copy, Todo), "copy() should return a Todo instance"


def test_todo_copy_preserves_text_and_done() -> None:
    """copy() should preserve text and done status."""
    original = Todo(id=1, text="buy milk", done=True)
    copy = original.copy()

    assert copy.text == original.text, "copy() should preserve text"
    assert copy.done == original.done, "copy() should preserve done status"


def test_todo_copy_generates_new_timestamps() -> None:
    """copy() should generate new timestamps."""
    original = Todo(id=1, text="buy milk", done=False)
    # Small delay to ensure different timestamp
    time.sleep(0.01)

    copy = original.copy()

    assert copy.created_at != original.created_at, "copy() should generate new created_at"
    assert copy.updated_at != original.updated_at, "copy() should generate new updated_at"


def test_todo_copy_accepts_new_id() -> None:
    """copy() should accept an optional new_id parameter."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy(new_id=42)

    assert copy.id == 42, "copy(new_id=42) should set id to 42"
    assert original.id == 1, "original id should remain unchanged"


def test_todo_copy_default_keeps_original_id() -> None:
    """copy() without new_id should keep the original id."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy()

    assert copy.id == original.id, "copy() without new_id should keep original id"


def test_todo_copy_is_independent() -> None:
    """Modifying the original should not affect the copy."""
    original = Todo(id=1, text="buy milk", done=False)
    copy = original.copy()

    # Modify the original
    original.text = "buy bread"
    original.done = True

    # Copy should be unchanged
    assert copy.text == "buy milk", "copy should be independent of original"
    assert copy.done is False, "copy should be independent of original"


def test_todo_copy_with_done_true() -> None:
    """copy() should work with done=True."""
    original = Todo(id=1, text="completed task", done=True)
    copy = original.copy()

    assert copy.done is True, "copy() should preserve done=True"
