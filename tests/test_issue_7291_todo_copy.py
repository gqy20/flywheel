"""Tests for Todo.copy method (Issue #7291).

These tests verify that:
1. copy() returns a new Todo instance with same content but different object
2. copy() preserves text and done status
3. copy() generates new timestamps (created_at/updated_at)
4. copy(with_id=True) preserves the original id
5. copy(with_id=False) uses id=0 for new instance
6. Modifying the copy does not affect the original
"""

from __future__ import annotations

import time

from flywheel.todo import Todo


def test_todo_copy_creates_new_instance() -> None:
    """copy() should return a new Todo instance (different object)."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy()

    assert copied is not original
    assert isinstance(copied, Todo)


def test_todo_copy_preserves_content() -> None:
    """copy() should preserve text and done status."""
    original = Todo(id=1, text="buy milk", done=True)
    copied = original.copy()

    assert copied.text == original.text
    assert copied.done == original.done


def test_todo_copy_new_timestamps() -> None:
    """copy() should generate new timestamps."""
    original = Todo(id=1, text="buy milk", done=False)
    # Small delay to ensure different timestamps
    time.sleep(0.01)
    copied = original.copy()

    assert copied.created_at != original.created_at
    assert copied.updated_at != original.updated_at
    # The copy's timestamps should be close to each other
    assert copied.created_at == copied.updated_at


def test_todo_copy_default_no_id() -> None:
    """copy() with with_id=False (default) should use id=0."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy()

    assert copied.id == 0
    assert original.id == 1  # Original unchanged


def test_todo_copy_with_id_true() -> None:
    """copy(with_id=True) should preserve the original id."""
    original = Todo(id=42, text="important task", done=True)
    copied = original.copy(with_id=True)

    assert copied.id == original.id == 42


def test_todo_copy_isolation() -> None:
    """Modifying the copy should not affect the original."""
    original = Todo(id=1, text="buy milk", done=False)
    copied = original.copy()

    # Modify the copy
    copied.text = "buy bread"
    copied.done = True
    copied.id = 999

    # Original should remain unchanged
    assert original.text == "buy milk"
    assert original.done is False
    assert original.id == 1


def test_todo_copy_with_done_false() -> None:
    """copy() should work correctly with done=False."""
    original = Todo(id=1, text="pending task", done=False)
    copied = original.copy()

    assert copied.done is False
    assert copied.text == "pending task"


def test_todo_copy_preserves_done_true() -> None:
    """copy() should preserve done=True status."""
    original = Todo(id=1, text="completed task", done=True)
    copied = original.copy()

    assert copied.done is True
