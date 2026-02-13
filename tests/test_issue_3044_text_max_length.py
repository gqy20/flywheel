"""Tests for Todo text max length validation (Issue #3044).

These tests verify that:
1. rename() method rejects text exceeding MAX_TEXT_LENGTH
2. from_dict() rejects data with text exceeding MAX_TEXT_LENGTH
3. Both methods accept text at exactly MAX_TEXT_LENGTH boundary
"""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo


class TestRenameMaxLength:
    """Tests for rename() method max length validation."""

    def test_rename_accepts_text_at_max_length(self) -> None:
        """rename() should accept text at exactly MAX_TEXT_LENGTH characters."""
        todo = Todo(id=1, text="original")
        max_text = "a" * MAX_TEXT_LENGTH
        todo.rename(max_text)
        assert todo.text == max_text

    def test_rename_rejects_text_exceeding_max_length(self) -> None:
        """rename() should reject text exceeding MAX_TEXT_LENGTH characters."""
        todo = Todo(id=1, text="original")
        too_long_text = "a" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError, match=r"exceeds.*maximum|too long|max.*length"):
            todo.rename(too_long_text)

    def test_rename_strips_then_validates_length(self) -> None:
        """rename() should strip first, then validate length."""
        todo = Todo(id=1, text="original")
        # Text that's exactly MAX_TEXT_LENGTH + 4 before strip (2 spaces each side),
        # but exactly MAX_TEXT_LENGTH after strip - should pass
        text_with_spaces = "  " + "a" * MAX_TEXT_LENGTH + "  "
        todo.rename(text_with_spaces)
        assert todo.text == "a" * MAX_TEXT_LENGTH

    def test_rename_rejects_text_exceeding_after_strip(self) -> None:
        """rename() should reject text that still exceeds limit after stripping."""
        todo = Todo(id=1, text="original")
        # Text that exceeds limit even after stripping spaces
        too_long_with_spaces = "  " + "a" * (MAX_TEXT_LENGTH + 1) + "  "
        with pytest.raises(ValueError, match=r"exceeds.*maximum|too long|max.*length"):
            todo.rename(too_long_with_spaces)


class TestFromDictMaxLength:
    """Tests for from_dict() method max length validation."""

    def test_from_dict_accepts_text_at_max_length(self) -> None:
        """from_dict() should accept text at exactly MAX_TEXT_LENGTH characters."""
        max_text = "b" * MAX_TEXT_LENGTH
        todo = Todo.from_dict({"id": 1, "text": max_text})
        assert todo.text == max_text

    def test_from_dict_rejects_text_exceeding_max_length(self) -> None:
        """from_dict() should reject text exceeding MAX_TEXT_LENGTH characters."""
        too_long_text = "c" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError, match=r"exceeds.*maximum|too long|max.*length"):
            Todo.from_dict({"id": 1, "text": too_long_text})

    def test_from_dict_rejects_text_with_spaces_exceeding_max_length(self) -> None:
        """from_dict() should reject text that exceeds limit including spaces."""
        # Unlike rename(), from_dict() doesn't strip, so spaces count
        too_long_with_spaces = "  " + "d" * (MAX_TEXT_LENGTH - 1) + "  "
        with pytest.raises(ValueError, match=r"exceeds.*maximum|too long|max.*length"):
            Todo.from_dict({"id": 1, "text": too_long_with_spaces})


class TestMaxLengthConstant:
    """Tests for MAX_TEXT_LENGTH constant."""

    def test_max_text_length_is_reasonable(self) -> None:
        """MAX_TEXT_LENGTH should be a positive integer (suggested: 1000)."""
        assert isinstance(MAX_TEXT_LENGTH, int)
        assert MAX_TEXT_LENGTH > 0
        # Issue suggests 1000 characters as reasonable limit
        assert MAX_TEXT_LENGTH == 1000
