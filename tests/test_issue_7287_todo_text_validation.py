"""Tests for Todo constructor text validation (Issue #7287).

These tests verify that the Todo constructor validates and strips text
in the same way that rename() does, ensuring consistent behavior
regardless of how a Todo is created.

Acceptance criteria:
- Todo(id=1, text='  ') should raise ValueError
- Todo(id=1, text='  task  ') should store 'task' (stripped)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorTextValidation:
    """Test text validation in Todo constructor via __post_init__."""

    def test_whitespace_only_text_raises_valueerror(self) -> None:
        """Todo with whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="   ")

    def test_empty_text_raises_valueerror(self) -> None:
        """Todo with empty text should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="")

    def test_tab_only_text_raises_valueerror(self) -> None:
        """Todo with tab-only text should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="\t\t")

    def test_mixed_whitespace_only_raises_valueerror(self) -> None:
        """Todo with mixed whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="  \t  \n  ")

    def test_text_with_leading_trailing_whitespace_is_stripped(self) -> None:
        """Todo text with leading/trailing whitespace should be stripped."""
        todo = Todo(id=1, text="  task  ")
        assert todo.text == "task"

    def test_text_with_leading_whitespace_is_stripped(self) -> None:
        """Todo text with leading whitespace should be stripped."""
        todo = Todo(id=1, text="   task")
        assert todo.text == "task"

    def test_text_with_trailing_whitespace_is_stripped(self) -> None:
        """Todo text with trailing whitespace should be stripped."""
        todo = Todo(id=1, text="task   ")
        assert todo.text == "task"

    def test_text_without_whitespace_unchanged(self) -> None:
        """Todo text without surrounding whitespace should be unchanged."""
        todo = Todo(id=1, text="task")
        assert todo.text == "task"

    def test_text_with_internal_whitespace_preserved(self) -> None:
        """Internal whitespace in text should be preserved."""
        todo = Todo(id=1, text="  buy milk  ")
        assert todo.text == "buy milk"


class TestTodoRenameConsistency:
    """Verify constructor behavior matches rename() behavior."""

    def test_constructor_strips_like_rename(self) -> None:
        """Both constructor and rename should strip text the same way."""
        todo = Todo(id=1, text="  initial  ")
        assert todo.text == "initial"

        todo.rename("  updated  ")
        assert todo.text == "updated"

    def test_constructor_rejects_empty_like_rename(self) -> None:
        """Both constructor and rename should reject empty text."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="  ")

        todo = Todo(id=1, text="valid")
        with pytest.raises(ValueError, match="cannot be empty"):
            todo.rename("  ")
