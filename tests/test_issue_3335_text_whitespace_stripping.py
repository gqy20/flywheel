"""Regression tests for issue #3335: inconsistent text whitespace stripping."""

import pytest

from flywheel.todo import Todo


class TestTodoFromDictStripsWhitespace:
    """Test that from_dict strips whitespace from text (matching rename behavior)."""

    def test_todo_from_dict_strips_whitespace_from_text(self) -> None:
        """from_dict should strip leading/trailing whitespace from text."""
        todo = Todo.from_dict({"id": 1, "text": "  hello  "})
        assert todo.text == "hello"

    def test_todo_from_dict_rejects_whitespace_only_text(self) -> None:
        """from_dict should reject text that is only whitespace."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})


class TestTodoInitStripsWhitespace:
    """Test that __init__ strips whitespace from text (matching rename behavior)."""

    def test_todo_init_strips_whitespace_from_text(self) -> None:
        """__init__ should strip leading/trailing whitespace from text."""
        todo = Todo(id=1, text="  hello  ")
        assert todo.text == "hello"

    def test_todo_init_rejects_whitespace_only_text(self) -> None:
        """__init__ should reject text that is only whitespace."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Todo(id=1, text="   ")


class TestTodoRenameConsistency:
    """Verify rename() behavior for reference."""

    def test_rename_strips_whitespace(self) -> None:
        """rename() strips whitespace (existing behavior)."""
        todo = Todo(id=1, text="original")
        todo.rename("  padded  ")
        assert todo.text == "padded"

    def test_rename_rejects_whitespace_only(self) -> None:
        """rename() rejects whitespace-only text (existing behavior)."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="cannot be empty"):
            todo.rename("   ")
