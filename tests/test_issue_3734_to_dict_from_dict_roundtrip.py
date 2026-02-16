"""Tests for to_dict/from_dict round-trip preservation (Issue #3734).

These tests verify that:
1. Todo.to_dict() -> Todo.from_dict() round-trip preserves all fields
2. All fields (id, text, done, created_at, updated_at) match after round-trip
3. Edge cases with special characters and long text work correctly
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_to_dict_from_dict_roundtrip_basic() -> None:
    """Basic round-trip test: to_dict -> from_dict should preserve all fields."""
    original = Todo(id=1, text="Buy groceries", done=False)
    original.created_at = "2024-01-15T10:30:00+00:00"
    original.updated_at = "2024-01-15T11:45:00+00:00"

    # Perform round-trip
    data = original.to_dict()
    restored = Todo.from_dict(data)

    # Verify all fields match
    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.done == original.done
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at


def test_todo_to_dict_from_dict_roundtrip_done_true() -> None:
    """Round-trip with done=True should preserve all fields."""
    original = Todo(id=42, text="Complete task", done=True)
    original.created_at = "2024-02-20T08:00:00+00:00"
    original.updated_at = "2024-02-20T09:30:00+00:00"

    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.id == original.id
    assert restored.text == original.text
    assert restored.done == original.done
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at


def test_todo_to_dict_from_dict_roundtrip_special_characters() -> None:
    """Round-trip with special characters in text should be preserved."""
    special_text = "Task with émojis 🎉, quotes \"'`, and symbols !@#$%^&*()"
    original = Todo(id=99, text=special_text, done=False)
    original.created_at = "2024-03-01T12:00:00+00:00"
    original.updated_at = "2024-03-01T12:00:00+00:00"

    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.id == original.id
    assert restored.text == special_text
    assert restored.done == original.done
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at


def test_todo_to_dict_from_dict_roundtrip_long_text() -> None:
    """Round-trip with long text should preserve all characters."""
    long_text = "A" * 10000  # 10,000 character string
    original = Todo(id=100, text=long_text, done=False)
    original.created_at = "2024-04-01T00:00:00+00:00"
    original.updated_at = "2024-04-01T00:00:00+00:00"

    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.id == original.id
    assert restored.text == long_text
    assert len(restored.text) == 10000
    assert restored.done == original.done
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at


def test_todo_to_dict_from_dict_roundtrip_newlines_and_tabs() -> None:
    """Round-trip with newlines, tabs, and other whitespace should be preserved."""
    text_with_whitespace = "Line 1\nLine 2\tTabbed\r\nWindows newline"
    original = Todo(id=200, text=text_with_whitespace, done=True)
    original.created_at = "2024-05-15T14:30:00+00:00"
    original.updated_at = "2024-05-15T15:45:00+00:00"

    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.id == original.id
    assert restored.text == text_with_whitespace
    assert restored.done == original.done
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at


def test_todo_to_dict_from_dict_roundtrip_unicode() -> None:
    """Round-trip with various Unicode characters should be preserved."""
    unicode_text = "中文 日本語 한국어 العربية עברית Ελληνικά Русский"
    original = Todo(id=300, text=unicode_text, done=False)
    original.created_at = "2024-06-20T08:00:00+00:00"
    original.updated_at = "2024-06-20T08:00:00+00:00"

    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.id == original.id
    assert restored.text == unicode_text
    assert restored.done == original.done
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at
