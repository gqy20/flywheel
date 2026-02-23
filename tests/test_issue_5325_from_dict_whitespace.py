"""Tests for Todo.from_dict whitespace handling (Issue #5325).

These tests verify the behavior of Todo.from_dict when text field contains
leading or trailing whitespace characters.

Note: Todo.from_dict preserves the original text value (does not strip),
which is different from Todo.rename() that strips whitespace.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_from_dict_preserves_text_with_leading_whitespace() -> None:
    """Todo.from_dict should preserve leading whitespace in text field."""
    todo = Todo.from_dict({"id": 1, "text": "  padded"})
    assert todo.text == "  padded"


def test_todo_from_dict_preserves_text_with_trailing_whitespace() -> None:
    """Todo.from_dict should preserve trailing whitespace in text field."""
    todo = Todo.from_dict({"id": 1, "text": "padded  "})
    assert todo.text == "padded  "


def test_todo_from_dict_preserves_text_with_leading_and_trailing_whitespace() -> None:
    """Todo.from_dict should preserve both leading and trailing whitespace in text."""
    todo = Todo.from_dict({"id": 1, "text": "  padded  "})
    assert todo.text == "  padded  "


def test_todo_from_dict_behavior_differs_from_rename() -> None:
    """Verify that from_dict preserves whitespace while rename strips it.

    This test documents the intentional difference in behavior:
    - from_dict: preserves original text (for loading stored data faithfully)
    - rename: strips whitespace (for user input sanitization)
    """
    # from_dict preserves whitespace
    todo = Todo.from_dict({"id": 1, "text": "  test  "})
    assert todo.text == "  test  "

    # rename strips whitespace
    todo.rename("  new text  ")
    assert todo.text == "new text"
