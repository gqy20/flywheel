"""Tests for todo text length limit (Issue #3777).

These tests verify that todo text has a maximum length limit to prevent
memory exhaustion attacks, matching the spirit of storage._MAX_JSON_SIZE_BYTES.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_constructor_rejects_text_exceeding_max_length() -> None:
    """Todo constructor should raise ValueError if text exceeds MAX_TEXT_LENGTH."""
    # Create text that exceeds the limit (10001 chars, assuming limit is 10000)
    long_text = "a" * 10001
    with pytest.raises(ValueError) as exc_info:
        Todo(id=1, text=long_text)

    assert "too long" in str(exc_info.value).lower()
    assert "10000" in str(exc_info.value)


def test_todo_constructor_accepts_text_at_max_length() -> None:
    """Todo constructor should accept text exactly at MAX_TEXT_LENGTH."""
    # Create text exactly at the limit (10000 chars)
    max_text = "a" * 10000
    todo = Todo(id=1, text=max_text)

    assert len(todo.text) == 10000
    assert todo.text == max_text


def test_todo_rename_rejects_text_exceeding_max_length() -> None:
    """Todo.rename() should raise ValueError if text exceeds MAX_TEXT_LENGTH."""
    todo = Todo(id=1, text="initial text")

    # Create text that exceeds the limit (10001 chars)
    long_text = "b" * 10001
    with pytest.raises(ValueError) as exc_info:
        todo.rename(long_text)

    assert "too long" in str(exc_info.value).lower()
    assert "10000" in str(exc_info.value)


def test_todo_rename_accepts_text_at_max_length() -> None:
    """Todo.rename() should accept text exactly at MAX_TEXT_LENGTH."""
    todo = Todo(id=1, text="initial text")

    # Create text exactly at the limit (10000 chars)
    max_text = "c" * 10000
    todo.rename(max_text)

    assert len(todo.text) == 10000
    assert todo.text == max_text


def test_todo_rename_strips_whitespace_before_length_check() -> None:
    """Whitespace is stripped before length check, so text+spaces can be longer."""
    todo = Todo(id=1, text="initial")

    # Create text that's exactly 10000 chars + surrounding whitespace
    text_with_whitespace = "   " + ("x" * 10000) + "   "
    todo.rename(text_with_whitespace)

    # Should succeed since stripped text is exactly 10000 chars
    assert len(todo.text) == 10000


def test_todo_from_dict_rejects_text_exceeding_max_length() -> None:
    """Todo.from_dict() should raise ValueError if text exceeds MAX_TEXT_LENGTH."""
    long_text = "d" * 10001
    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict({"id": 1, "text": long_text})

    assert "too long" in str(exc_info.value).lower()
    assert "10000" in str(exc_info.value)
