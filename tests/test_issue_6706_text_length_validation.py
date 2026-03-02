"""Tests for text length validation (Issue #6706).

These tests verify that:
1. Todo text has a configurable maximum length (default 1000 chars)
2. ValueError is raised when text exceeds MAX_TEXT_LENGTH
3. Error message clearly states the limit and actual length
4. Validation applies to constructor, rename(), and from_dict()
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTextLengthValidation:
    """Tests for MAX_TEXT_LENGTH validation."""

    def test_max_text_length_constant_exists(self) -> None:
        """Todo class should have MAX_TEXT_LENGTH constant."""
        from flywheel.todo import Todo

        assert hasattr(Todo, "MAX_TEXT_LENGTH")
        assert Todo.MAX_TEXT_LENGTH == 1000

    def test_text_exactly_at_limit_accepted(self) -> None:
        """Text at exactly MAX_TEXT_LENGTH (1000 chars) should be accepted."""
        text_at_limit = "a" * 1000
        todo = Todo(id=1, text=text_at_limit)
        assert len(todo.text) == 1000

    def test_text_exceeds_limit_raises_error(self) -> None:
        """Text exceeding MAX_TEXT_LENGTH (1001 chars) should raise ValueError."""
        text_over_limit = "a" * 1001
        with pytest.raises(ValueError) as exc_info:
            Todo(id=1, text=text_over_limit)

        # Error message should state the limit and actual length
        error_msg = str(exc_info.value)
        assert "1000" in error_msg
        assert "1001" in error_msg

    def test_rename_exceeds_limit_raises_error(self) -> None:
        """rename() with text exceeding limit should raise ValueError."""
        todo = Todo(id=1, text="valid text")
        text_over_limit = "b" * 1001

        with pytest.raises(ValueError) as exc_info:
            todo.rename(text_over_limit)

        error_msg = str(exc_info.value)
        assert "1000" in error_msg
        assert "1001" in error_msg

    def test_rename_at_limit_accepted(self) -> None:
        """rename() with text at exactly limit should be accepted."""
        todo = Todo(id=1, text="valid text")
        text_at_limit = "c" * 1000

        todo.rename(text_at_limit)
        assert len(todo.text) == 1000

    def test_from_dict_exceeds_limit_raises_error(self) -> None:
        """from_dict() with oversized text should raise ValueError."""
        text_over_limit = "d" * 1001
        data = {"id": 1, "text": text_over_limit}

        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict(data)

        error_msg = str(exc_info.value)
        assert "1000" in error_msg
        assert "1001" in error_msg

    def test_from_dict_at_limit_accepted(self) -> None:
        """from_dict() with text at exactly limit should be accepted."""
        text_at_limit = "e" * 1000
        data = {"id": 1, "text": text_at_limit}

        todo = Todo.from_dict(data)
        assert len(todo.text) == 1000

    def test_empty_string_still_raises_error(self) -> None:
        """Empty string should still raise ValueError (existing behavior)."""
        with pytest.raises(ValueError) as exc_info:
            Todo(id=1, text="")

        assert "empty" in str(exc_info.value).lower()

    def test_whitespace_only_still_raises_error(self) -> None:
        """Whitespace-only string should still raise ValueError after strip."""
        with pytest.raises(ValueError) as exc_info:
            Todo(id=1, text="   ")

        assert "empty" in str(exc_info.value).lower()
