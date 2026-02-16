"""Tests for text length validation (Issue #3624).

These tests verify that:
1. Todo text exceeding 10000 characters raises ValueError
2. Error message includes actual length and max length
3. Validation applies to both __post_init__ and rename()
4. Normal-length text (<=10000 chars) is unaffected
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoTextLengthValidation:
    """Tests for text length validation on Todo."""

    def test_rename_rejects_text_exceeding_max_length(self) -> None:
        """rename() should reject text longer than 10000 characters."""
        todo = Todo(id=1, text="original")
        original_updated_at = todo.updated_at

        # Create text that exceeds the limit (10001 chars)
        long_text = "x" * 10001

        with pytest.raises(ValueError) as exc_info:
            todo.rename(long_text)

        # Verify error message includes both actual and max length
        error_msg = str(exc_info.value)
        assert "10001" in error_msg
        assert "10000" in error_msg

        # Verify state unchanged after failed validation
        assert todo.text == "original"
        assert todo.updated_at == original_updated_at

    def test_rename_accepts_text_at_max_length(self) -> None:
        """rename() should accept text exactly at the limit (10000 chars)."""
        todo = Todo(id=1, text="original")

        # Create text exactly at the limit (10000 chars)
        max_text = "x" * 10000

        # Should succeed without raising
        todo.rename(max_text)
        assert todo.text == max_text

    def test_rename_accepts_text_below_max_length(self) -> None:
        """rename() should accept text below the limit (9999 chars)."""
        todo = Todo(id=1, text="original")

        # Create text just below the limit (9999 chars)
        text_below_limit = "x" * 9999

        # Should succeed without raising
        todo.rename(text_below_limit)
        assert todo.text == text_below_limit

    def test_post_init_rejects_text_exceeding_max_length(self) -> None:
        """__post_init__ should reject text longer than 10000 characters."""
        # Create text that exceeds the limit (10001 chars)
        long_text = "x" * 10001

        with pytest.raises(ValueError) as exc_info:
            Todo(id=1, text=long_text)

        # Verify error message includes both actual and max length
        error_msg = str(exc_info.value)
        assert "10001" in error_msg
        assert "10000" in error_msg

    def test_post_init_accepts_text_at_max_length(self) -> None:
        """__post_init__ should accept text exactly at the limit (10000 chars)."""
        # Create text exactly at the limit (10000 chars)
        max_text = "x" * 10000

        # Should succeed without raising
        todo = Todo(id=1, text=max_text)
        assert todo.text == max_text

    def test_post_init_accepts_normal_text(self) -> None:
        """__post_init__ should accept normal-length text."""
        # Normal text should work fine
        todo = Todo(id=1, text="normal todo text")
        assert todo.text == "normal todo text"
