"""Regression tests for Issue #2881: from_dict text field validation.

This test file ensures that Todo.from_dict validates text field content:
1. Rejects NUL characters (\x00) to prevent potential security issues
2. Rejects excessive text length (>10000 chars) to prevent DoS via storage bloat
"""

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_null_byte_in_text() -> None:
    """Todo.from_dict should reject text containing NUL character (\x00)."""
    with pytest.raises(ValueError, match=r"NUL character|\\x00|null byte"):
        Todo.from_dict({"id": 1, "text": "buy\x00milk"})


def test_from_dict_rejects_null_byte_at_start() -> None:
    """Todo.from_dict should reject text starting with NUL character."""
    with pytest.raises(ValueError, match=r"NUL character|\\x00|null byte"):
        Todo.from_dict({"id": 1, "text": "\x00milk"})


def test_from_dict_rejects_null_byte_at_end() -> None:
    """Todo.from_dict should reject text ending with NUL character."""
    with pytest.raises(ValueError, match=r"NUL character|\\x00|null byte"):
        Todo.from_dict({"id": 1, "text": "milk\x00"})


def test_from_dict_rejects_multiple_null_bytes() -> None:
    """Todo.from_dict should reject text with multiple NUL characters."""
    with pytest.raises(ValueError, match=r"NUL character|\\x00|null byte"):
        Todo.from_dict({"id": 1, "text": "buy\x00\x00milk"})


def test_from_dict_rejects_excessive_length() -> None:
    """Todo.from_dict should reject text longer than 10000 characters."""
    with pytest.raises(ValueError, match=r"length|exceeds|too long"):
        Todo.from_dict({"id": 1, "text": "a" * 10001})


def test_from_dict_accepts_max_length() -> None:
    """Todo.from_dict should accept text with exactly 10000 characters."""
    todo = Todo.from_dict({"id": 1, "text": "a" * 10000})
    assert todo.text == "a" * 10000


def test_from_dict_accepts_normal_text() -> None:
    """Todo.from_dict should accept normal text without control characters."""
    todo = Todo.from_dict({"id": 1, "text": "Buy groceries"})
    assert todo.text == "Buy groceries"


def test_from_dict_accepts_unicode_text() -> None:
    """Todo.from_dict should accept Unicode text (not to be confused with C1)."""
    todo = Todo.from_dict({"id": 1, "text": "Buy café and 日本語"})
    assert todo.text == "Buy café and 日本語"


def test_from_dict_accepts_newlines_in_text() -> None:
    """Todo.from_dict should accept newlines (formatter handles escaping)."""
    todo = Todo.from_dict({"id": 1, "text": "Line1\nLine2"})
    assert todo.text == "Line1\nLine2"


def test_from_dict_accepts_tabs_in_text() -> None:
    """Todo.from_dict should accept tabs (formatter handles escaping)."""
    todo = Todo.from_dict({"id": 1, "text": "Task\twith\ttabs"})
    assert todo.text == "Task\twith\ttabs"
