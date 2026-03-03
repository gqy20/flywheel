"""Regression tests for Issue #6927: Todo text maximum length validation.

These tests verify that:
1. Todo text exceeding 10000 characters is rejected
2. rename() rejects oversized text
3. from_dict() rejects oversized text
4. Boundary value (10000 chars) works correctly
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo

MAX_TEXT_LENGTH = 10000


class TestTodoRenameRejectsOversizedText:
    """Tests for rename() rejecting oversized text."""

    def test_rename_rejects_text_over_10000_chars(self) -> None:
        """rename() should reject text exceeding 10000 characters."""
        todo = Todo(id=1, text="valid text")
        oversized_text = "a" * (MAX_TEXT_LENGTH + 1)

        with pytest.raises(ValueError, match="exceeds maximum length"):
            todo.rename(oversized_text)

    def test_rename_accepts_exactly_10000_chars(self) -> None:
        """rename() should accept text of exactly 10000 characters."""
        todo = Todo(id=1, text="valid text")
        max_text = "a" * MAX_TEXT_LENGTH

        # Should not raise
        todo.rename(max_text)
        assert len(todo.text) == MAX_TEXT_LENGTH


class TestTodoFromDictRejectsOversizedText:
    """Tests for from_dict() rejecting oversized text."""

    def test_from_dict_rejects_text_over_10000_chars(self) -> None:
        """from_dict() should reject text exceeding 10000 characters."""
        oversized_text = "a" * (MAX_TEXT_LENGTH + 1)
        data = {"id": 1, "text": oversized_text}

        with pytest.raises(ValueError, match="exceeds maximum length"):
            Todo.from_dict(data)

    def test_from_dict_accepts_exactly_10000_chars(self) -> None:
        """from_dict() should accept text of exactly 10000 characters."""
        max_text = "a" * MAX_TEXT_LENGTH
        data = {"id": 1, "text": max_text}

        # Should not raise
        todo = Todo.from_dict(data)
        assert len(todo.text) == MAX_TEXT_LENGTH


class TestTodoConstructorRejectsOversizedText:
    """Tests for Todo constructor rejecting oversized text."""

    def test_constructor_rejects_text_over_10000_chars(self) -> None:
        """Todo constructor should reject text exceeding 10000 characters."""
        oversized_text = "a" * (MAX_TEXT_LENGTH + 1)

        with pytest.raises(ValueError, match="exceeds maximum length"):
            Todo(id=1, text=oversized_text)

    def test_constructor_accepts_exactly_10000_chars(self) -> None:
        """Todo constructor should accept text of exactly 10000 characters."""
        max_text = "a" * MAX_TEXT_LENGTH

        # Should not raise
        todo = Todo(id=1, text=max_text)
        assert len(todo.text) == MAX_TEXT_LENGTH
