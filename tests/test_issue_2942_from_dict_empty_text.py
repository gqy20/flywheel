"""Regression tests for issue #2942: Todo.from_dict rejects empty/whitespace text."""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_empty_string() -> None:
    """Bug #2942: Todo.from_dict() should reject empty string for text."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo.from_dict({"id": 1, "text": ""})


def test_from_dict_rejects_whitespace_only() -> None:
    """Bug #2942: Todo.from_dict() should reject whitespace-only text."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Todo.from_dict({"id": 1, "text": " "})

    with pytest.raises(ValueError, match="cannot be empty"):
        Todo.from_dict({"id": 1, "text": "\t\n  "})


def test_from_dict_accepts_valid_text() -> None:
    """Bug #2942: Todo.from_dict() should accept valid text."""
    # Normal text should work
    todo = Todo.from_dict({"id": 1, "text": "valid todo"})
    assert todo.text == "valid todo"

    # Text with leading/trailing whitespace should be accepted (stripped)
    todo2 = Todo.from_dict({"id": 2, "text": "  padded  "})
    assert todo2.text == "  padded  "  # from_dict preserves original
