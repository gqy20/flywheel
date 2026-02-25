"""Regression test for issue #5830.

Bug: Todo.__init__ and from_dict accept empty/whitespace-only text without validation.

This test ensures that:
- Todo(id=1, text='') raises ValueError with message 'Todo text cannot be empty'
- Todo(id=1, text='   ') raises ValueError
- Todo.from_dict({'id': 1, 'text': ''}) raises ValueError
- Todo.from_dict({'id': 1, 'text': '   '}) raises ValueError
"""

import pytest

from flywheel.todo import Todo


class TestTodoEmptyTextValidation:
    """Test that Todo rejects empty/whitespace-only text consistently."""

    def test_init_with_empty_string_raises_value_error(self) -> None:
        """Todo.__init__ should raise ValueError for empty text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="")

    def test_init_with_whitespace_only_raises_value_error(self) -> None:
        """Todo.__init__ should raise ValueError for whitespace-only text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="   ")

    def test_init_with_tabs_only_raises_value_error(self) -> None:
        """Todo.__init__ should raise ValueError for tabs-only text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="\t\t")

    def test_init_with_mixed_whitespace_only_raises_value_error(self) -> None:
        """Todo.__init__ should raise ValueError for mixed whitespace-only text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo(id=1, text="  \t  \n  ")

    def test_from_dict_with_empty_string_raises_value_error(self) -> None:
        """Todo.from_dict should raise ValueError for empty text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": ""})

    def test_from_dict_with_whitespace_only_raises_value_error(self) -> None:
        """Todo.from_dict should raise ValueError for whitespace-only text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "   "})

    def test_from_dict_with_tabs_only_raises_value_error(self) -> None:
        """Todo.from_dict should raise ValueError for tabs-only text."""
        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            Todo.from_dict({"id": 1, "text": "\t\t"})

    def test_init_with_valid_text_succeeds(self) -> None:
        """Todo.__init__ should accept valid text."""
        todo = Todo(id=1, text="Buy groceries")
        assert todo.text == "Buy groceries"

    def test_init_with_text_having_leading_trailing_whitespace_strips(self) -> None:
        """Todo.__init__ should strip leading/trailing whitespace from text."""
        # Following rename() behavior, text should be stripped
        todo = Todo(id=1, text="  Buy groceries  ")
        assert todo.text == "Buy groceries"

    def test_from_dict_with_valid_text_succeeds(self) -> None:
        """Todo.from_dict should accept valid text."""
        todo = Todo.from_dict({"id": 1, "text": "Buy groceries"})
        assert todo.text == "Buy groceries"
