"""Tests for Issue #7219: Todo.from_dict should reject empty/whitespace-only text.

This test ensures that Todo.from_dict validates text field consistently with Todo.rename:
- Todo.from_dict({'id': 1, 'text': ''}) should raise ValueError
- Todo.from_dict({'id': 1, 'text': ' '}) should raise ValueError
- Todo.from_dict({'id': 1, 'text': ' valid '}) should preserve original whitespace
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_empty_text() -> None:
    """Bug #7219: Todo.from_dict should reject empty string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|blank|text"):
        Todo.from_dict({"id": 1, "text": ""})


def test_todo_from_dict_rejects_whitespace_only_text() -> None:
    """Bug #7219: Todo.from_dict should reject whitespace-only string for 'text' field."""
    with pytest.raises(ValueError, match=r"empty|blank|text"):
        Todo.from_dict({"id": 1, "text": " "})

    with pytest.raises(ValueError, match=r"empty|blank|text"):
        Todo.from_dict({"id": 1, "text": "\t\n  "})


def test_todo_from_dict_preserves_valid_whitespace() -> None:
    """Bug #7219: Todo.from_dict should preserve original whitespace for valid text."""
    # Text with surrounding whitespace should be preserved (not stripped)
    todo = Todo.from_dict({"id": 1, "text": " valid "})
    assert todo.text == " valid "

    # Text with internal whitespace should work
    todo2 = Todo.from_dict({"id": 2, "text": "hello world"})
    assert todo2.text == "hello world"
