"""Tests for text maximum length validation (Issue #3044).

These tests verify that:
1. rename() method accepts text at the boundary length
2. rename() method rejects text that exceeds the maximum length
3. from_dict() rejects text that exceeds the maximum length
"""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo


class TestRenameTextLengthValidation:
    """Tests for rename() method text length validation."""

    def test_rename_accepts_boundary_length_text(self) -> None:
        """rename() should accept text exactly at MAX_TEXT_LENGTH."""
        todo = Todo(id=1, text="original")
        boundary_text = "x" * MAX_TEXT_LENGTH
        todo.rename(boundary_text)
        assert todo.text == boundary_text

    def test_rename_rejects_text_exceeding_max_length(self) -> None:
        """rename() should raise ValueError for text exceeding MAX_TEXT_LENGTH."""
        todo = Todo(id=1, text="original")
        too_long_text = "x" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError, match=r"text.*too long|exceeds.*maximum|maximum.*length"):
            todo.rename(too_long_text)

    def test_rename_accepts_shorter_text(self) -> None:
        """rename() should accept text shorter than MAX_TEXT_LENGTH."""
        todo = Todo(id=1, text="original")
        short_text = "short"
        todo.rename(short_text)
        assert todo.text == short_text


class TestFromDictTextLengthValidation:
    """Tests for from_dict() method text length validation."""

    def test_from_dict_rejects_text_exceeding_max_length(self) -> None:
        """from_dict() should raise ValueError for text exceeding MAX_TEXT_LENGTH."""
        too_long_text = "x" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError, match=r"text.*too long|exceeds.*maximum|maximum.*length"):
            Todo.from_dict({"id": 1, "text": too_long_text})

    def test_from_dict_accepts_boundary_length_text(self) -> None:
        """from_dict() should accept text exactly at MAX_TEXT_LENGTH."""
        boundary_text = "y" * MAX_TEXT_LENGTH
        todo = Todo.from_dict({"id": 1, "text": boundary_text})
        assert todo.text == boundary_text

    def test_from_dict_accepts_shorter_text(self) -> None:
        """from_dict() should accept text shorter than MAX_TEXT_LENGTH."""
        short_text = "short text"
        todo = Todo.from_dict({"id": 1, "text": short_text})
        assert todo.text == short_text


class TestMaxTextLengthConstant:
    """Tests for MAX_TEXT_LENGTH constant."""

    def test_max_text_length_is_defined(self) -> None:
        """MAX_TEXT_LENGTH should be defined and be a positive integer."""
        assert isinstance(MAX_TEXT_LENGTH, int)
        assert MAX_TEXT_LENGTH > 0

    def test_max_text_length_is_reasonable(self) -> None:
        """MAX_TEXT_LENGTH should be a reasonable value (1000 as specified)."""
        assert MAX_TEXT_LENGTH == 1000
