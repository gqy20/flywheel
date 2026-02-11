"""Tests for rename() whitespace validation (Issue #2789).

These tests verify that:
1. rename() rejects pure whitespace strings (e.g., ' ', '\t', '\n')
2. rename() strips leading/trailing whitespace from valid text
3. The validation logic is consistent across rename() and add()
"""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp
from flywheel.todo import Todo


class TestTodoRenameWhitespaceValidation:
    """Test Todo.rename() handles whitespace correctly."""

    def test_rename_raises_on_single_space(self) -> None:
        """rename(' ') should raise ValueError."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename(" ")

    def test_rename_raises_on_multiple_spaces(self) -> None:
        """rename('   ') should raise ValueError."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("   ")

    def test_rename_raises_on_tabs(self) -> None:
        """rename('\\t') should raise ValueError."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("\t")

    def test_rename_raises_on_newlines(self) -> None:
        """rename('\\n') should raise ValueError."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename("\n")

    def test_rename_raises_on_mixed_whitespace(self) -> None:
        """rename(' \\t\\n ') should raise ValueError."""
        todo = Todo(id=1, text="original")
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.rename(" \t\n ")

    def test_rename_strips_leading_trailing_spaces(self) -> None:
        """rename(' valid ') should store 'valid'."""
        todo = Todo(id=1, text="original")
        todo.rename(" valid ")
        assert todo.text == "valid"

    def test_rename_strips_tabs(self) -> None:
        """rename('\\tvalid\\t') should store 'valid'."""
        todo = Todo(id=1, text="original")
        todo.rename("\tvalid\t")
        assert todo.text == "valid"

    def test_rename_allows_internal_spaces(self) -> None:
        """rename should preserve internal spaces."""
        todo = Todo(id=1, text="original")
        todo.rename("multi word task")
        assert todo.text == "multi word task"

    def test_rename_updates_timestamp(self) -> None:
        """rename should update the updated_at timestamp."""
        todo = Todo(id=1, text="original")
        original_updated = todo.updated_at
        import time
        time.sleep(0.01)  # Small delay to ensure timestamp difference
        todo.rename("new text")
        assert todo.updated_at != original_updated


class TestTodoAppAddWhitespaceValidation:
    """Test TodoApp.add() handles whitespace correctly."""

    def test_add_raises_on_single_space(self, tmp_path) -> None:
        """add(' ') should raise ValueError."""
        db_path = tmp_path / ".todo.json"
        app = TodoApp(db_path=str(db_path))
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            app.add(" ")

    def test_add_raises_on_multiple_spaces(self, tmp_path) -> None:
        """add('   ') should raise ValueError."""
        db_path = tmp_path / ".todo.json"
        app = TodoApp(db_path=str(db_path))
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            app.add("   ")

    def test_add_raises_on_tabs(self, tmp_path) -> None:
        """add('\\t') should raise ValueError."""
        db_path = tmp_path / ".todo.json"
        app = TodoApp(db_path=str(db_path))
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            app.add("\t")

    def test_add_strips_leading_trailing_spaces(self, tmp_path) -> None:
        """add(' valid ') should store 'valid'."""
        db_path = tmp_path / ".todo.json"
        app = TodoApp(db_path=str(db_path))
        todo = app.add(" valid task ")
        assert todo.text == "valid task"

    def test_add_allows_internal_spaces(self, tmp_path) -> None:
        """add should preserve internal spaces."""
        db_path = tmp_path / ".todo.json"
        app = TodoApp(db_path=str(db_path))
        todo = app.add("multi word task")
        assert todo.text == "multi word task"
