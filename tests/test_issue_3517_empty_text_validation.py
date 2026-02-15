"""Tests for Issue #3517: Todo and Todo.from_dict should reject empty/whitespace-only text.

These tests verify that:
1. Todo() constructor rejects empty or whitespace-only text
2. Todo.from_dict() rejects empty or whitespace-only text
3. Behavior is consistent with rename() method
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoConstructorRejectsEmptyText:
    """Bug #3517: Todo() constructor should reject empty or whitespace-only text."""

    def test_todo_constructor_rejects_empty_string(self) -> None:
        """Todo(id=1, text='') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_todo_constructor_rejects_whitespace_only_string(self) -> None:
        """Todo(id=1, text=' ') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text=" ")

    def test_todo_constructor_rejects_mixed_whitespace(self) -> None:
        """Todo(id=1, text=' \\t\\n') should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text=" \t\n")

    def test_todo_constructor_accepts_valid_text(self) -> None:
        """Todo(id=1, text='valid') should create successfully."""
        todo = Todo(id=1, text="valid")
        assert todo.text == "valid"

    def test_todo_constructor_strips_and_validates_text(self) -> None:
        """Todo constructor should strip whitespace and then validate."""
        # Text with leading/trailing whitespace should be stripped
        todo = Todo(id=1, text="  valid  ")
        assert todo.text == "valid"


class TestTodoFromDictRejectsEmptyText:
    """Bug #3517: Todo.from_dict() should reject empty or whitespace-only text."""

    def test_from_dict_rejects_empty_string(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_rejects_whitespace_only_string(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ' '}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": " "})

    def test_from_dict_rejects_mixed_whitespace(self) -> None:
        """Todo.from_dict({'id': 1, 'text': ' \\t\\n'}) should raise ValueError."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": " \t\n"})

    def test_from_dict_accepts_valid_text(self) -> None:
        """Todo.from_dict({'id': 1, 'text': 'valid'}) should create successfully."""
        todo = Todo.from_dict({"id": 1, "text": "valid"})
        assert todo.text == "valid"

    def test_from_dict_strips_and_validates_text(self) -> None:
        """Todo.from_dict should strip whitespace and then validate."""
        todo = Todo.from_dict({"id": 1, "text": "  valid  "})
        assert todo.text == "valid"
