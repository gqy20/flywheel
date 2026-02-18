"""Tests for todo text max length validation (Issue #4259).

These tests verify that:
1. Todo.rename() rejects text longer than MAX_TEXT_LENGTH
2. Todo.from_dict() rejects data['text'] longer than MAX_TEXT_LENGTH
3. Text at exactly MAX_TEXT_LENGTH succeeds
"""

from __future__ import annotations

import pytest

from flywheel.todo import MAX_TEXT_LENGTH, Todo


class TestRenameTextMaxLength:
    """Tests for rename() max length validation."""

    def test_rename_text_at_max_length_succeeds(self) -> None:
        """Text at exactly MAX_TEXT_LENGTH should be accepted."""
        todo = Todo(id=1, text="original")
        max_length_text = "a" * MAX_TEXT_LENGTH
        todo.rename(max_length_text)
        assert todo.text == max_length_text

    def test_rename_text_exceeds_max_length_raises(self) -> None:
        """Text exceeding MAX_TEXT_LENGTH should raise ValueError."""
        todo = Todo(id=1, text="original")
        too_long_text = "a" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError, match=r"cannot exceed|exceeds.*limit|too long"):
            todo.rename(too_long_text)


class TestFromDictTextMaxLength:
    """Tests for from_dict() max length validation."""

    def test_from_dict_text_at_max_length_succeeds(self) -> None:
        """from_dict should accept text at exactly MAX_TEXT_LENGTH."""
        max_length_text = "a" * MAX_TEXT_LENGTH
        todo = Todo.from_dict({"id": 1, "text": max_length_text})
        assert todo.text == max_length_text

    def test_from_dict_text_exceeds_max_length_raises(self) -> None:
        """from_dict should reject text exceeding MAX_TEXT_LENGTH."""
        too_long_text = "a" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError, match=r"cannot exceed|exceeds.*limit|too long"):
            Todo.from_dict({"id": 1, "text": too_long_text})
