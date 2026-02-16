"""Tests for text length validation in Todo.

Issue #3624: Add text length validation to prevent oversized input.

This protects against:
1) JSON file bloat affecting performance
2) Terminal output confusion
3) Works with storage.py's 10MB limit for multi-layer protection
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo

# Constants should match src/flywheel/todo.py
_MAX_TEXT_LENGTH = 10000


class TestTodoTextLengthValidation:
    """Tests for text length validation in rename() and __post_init__."""

    def test_rename_rejects_text_exceeding_max_length(self) -> None:
        """Issue #3624: rename() should reject text longer than 10000 chars."""
        todo = Todo(id=1, text="original")
        original_updated_at = todo.updated_at

        # Create text that exceeds max length (10001 chars)
        long_text = "x" * 10001

        with pytest.raises(ValueError) as exc_info:
            todo.rename(long_text)

        # Verify error message contains actual and max lengths
        error_msg = str(exc_info.value)
        assert "too long" in error_msg.lower()
        assert "10001" in error_msg
        assert "10000" in error_msg

        # Verify state unchanged after failed validation
        assert todo.text == "original"
        assert todo.updated_at == original_updated_at

    def test_rename_accepts_text_at_max_length(self) -> None:
        """Issue #3624: rename() should accept text at exactly 10000 chars."""
        todo = Todo(id=1, text="original")

        # Create text at max length (exactly 10000 chars)
        max_length_text = "x" * _MAX_TEXT_LENGTH

        # Should work without error
        todo.rename(max_length_text)
        assert todo.text == max_length_text
        assert len(todo.text) == _MAX_TEXT_LENGTH

    def test_rename_accepts_text_below_max_length(self) -> None:
        """Issue #3624: rename() should accept text at 9999 chars (below max)."""
        todo = Todo(id=1, text="original")

        # Create text below max length (9999 chars)
        below_max_text = "y" * (_MAX_TEXT_LENGTH - 1)

        # Should work without error
        todo.rename(below_max_text)
        assert todo.text == below_max_text

    def test_post_init_rejects_text_exceeding_max_length(self) -> None:
        """Issue #3624: Todo construction should reject text longer than 10000 chars."""
        long_text = "z" * 10001

        with pytest.raises(ValueError) as exc_info:
            Todo(id=1, text=long_text)

        # Verify error message contains actual and max lengths
        error_msg = str(exc_info.value)
        assert "too long" in error_msg.lower()
        assert "10001" in error_msg
        assert "10000" in error_msg

    def test_post_init_accepts_text_at_max_length(self) -> None:
        """Issue #3624: Todo construction should accept text at exactly 10000 chars."""
        max_length_text = "a" * _MAX_TEXT_LENGTH

        # Should work without error
        todo = Todo(id=1, text=max_length_text)
        assert todo.text == max_length_text
        assert len(todo.text) == _MAX_TEXT_LENGTH

    def test_post_init_accepts_text_below_max_length(self) -> None:
        """Issue #3624: Todo construction should accept text at 9999 chars."""
        below_max_text = "b" * (_MAX_TEXT_LENGTH - 1)

        # Should work without error
        todo = Todo(id=1, text=below_max_text)
        assert todo.text == below_max_text

    def test_rename_strips_whitespace_before_length_check(self) -> None:
        """Issue #3624: rename() strips whitespace, then validates length."""
        todo = Todo(id=1, text="original")

        # Create text with padding that exceeds max length after strip
        # After strip, it should be exactly at max length (10000 chars)
        padded_text = "  " + ("x" * _MAX_TEXT_LENGTH) + "  "

        # Should work because after strip it's exactly at max length
        todo.rename(padded_text)
        assert todo.text == "x" * _MAX_TEXT_LENGTH

    def test_from_dict_rejects_text_exceeding_max_length(self) -> None:
        """Issue #3624: from_dict should also validate text length."""
        long_text = "c" * 10001
        data = {"id": 1, "text": long_text}

        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict(data)

        # Verify error message contains actual and max lengths
        error_msg = str(exc_info.value)
        assert "too long" in error_msg.lower()
        assert "10001" in error_msg
        assert "10000" in error_msg

    def test_from_dict_accepts_text_at_max_length(self) -> None:
        """Issue #3624: from_dict should accept text at exactly 10000 chars."""
        max_length_text = "d" * _MAX_TEXT_LENGTH
        data = {"id": 1, "text": max_length_text}

        # Should work without error
        todo = Todo.from_dict(data)
        assert todo.text == max_length_text
