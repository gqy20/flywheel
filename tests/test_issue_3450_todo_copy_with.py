"""Tests for Todo.copy_with method (Issue #3450).

These tests verify that:
1. copy_with returns a new Todo instance with specified fields overridden
2. The original Todo is not modified (immutability)
3. Unspecified fields are copied from the original
4. updated_at is automatically updated to current time
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_copy_with_returns_new_instance() -> None:
    """copy_with should return a new Todo instance, not the same object."""
    t1 = Todo(id=1, text="original")
    t2 = t1.copy_with(done=True)

    assert t2 is not t1
    assert isinstance(t2, Todo)


def test_copy_with_original_unchanged() -> None:
    """The original Todo should remain unchanged after copy_with."""
    t1 = Todo(id=1, text="a")
    _ = t1.copy_with(done=True)

    # Original should not be modified
    assert not t1.done


def test_copy_with_overrides_done() -> None:
    """copy_with should correctly override the done field."""
    t1 = Todo(id=1, text="a", done=False)
    t2 = t1.copy_with(done=True)

    assert t2.done is True
    assert t2.id == t1.id
    assert t2.text == "a"


def test_copy_with_preserves_unspecified_fields() -> None:
    """copy_with should preserve fields that are not specified."""
    t1 = Todo(id=1, text="original text")
    t2 = t1.copy_with(done=True)

    # id and text should be preserved
    assert t2.id == 1
    assert t2.text == "original text"
    assert t2.done is True


def test_copy_with_updates_timestamp() -> None:
    """copy_with should update updated_at to current time."""
    import time

    t1 = Todo(id=1, text="a")
    original_updated_at = t1.updated_at

    # Small delay to ensure different timestamp
    time.sleep(0.01)

    t2 = t1.copy_with(done=True)

    # new instance should have different updated_at
    assert t2.updated_at != original_updated_at
    # original should remain unchanged
    assert t1.updated_at == original_updated_at


def test_copy_with_override_text() -> None:
    """copy_with should allow overriding text field."""
    t1 = Todo(id=1, text="old text")
    t2 = t1.copy_with(text="new text")

    assert t2.text == "new text"
    assert t1.text == "old text"


def test_copy_with_override_id() -> None:
    """copy_with should allow overriding id field."""
    t1 = Todo(id=1, text="task")
    t2 = t1.copy_with(id=99)

    assert t2.id == 99
    assert t1.id == 1


def test_copy_with_multiple_overrides() -> None:
    """copy_with should allow overriding multiple fields at once."""
    t1 = Todo(id=1, text="old", done=False)
    t2 = t1.copy_with(id=2, text="new", done=True)

    assert t2.id == 2
    assert t2.text == "new"
    assert t2.done is True
    # Original unchanged
    assert t1.id == 1
    assert t1.text == "old"
    assert not t1.done


def test_copy_with_no_args_returns_copy() -> None:
    """copy_with with no arguments should return a copy with updated timestamp."""
    import time

    t1 = Todo(id=1, text="a")
    original_updated_at = t1.updated_at

    time.sleep(0.01)

    t2 = t1.copy_with()

    # Should be different object
    assert t2 is not t1
    # All fields should match except updated_at
    assert t2.id == t1.id
    assert t2.text == t1.text
    assert t2.done == t1.done
    assert t2.created_at == t1.created_at
    # Timestamp should be updated
    assert t2.updated_at != original_updated_at


def test_copy_with_preserves_created_at() -> None:
    """copy_with should preserve created_at unless explicitly overridden."""
    t1 = Todo(id=1, text="a")
    t2 = t1.copy_with(done=True)

    # created_at should be preserved
    assert t2.created_at == t1.created_at
