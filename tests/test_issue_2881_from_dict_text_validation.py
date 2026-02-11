"""Regression tests for Issue #2881: from_dict text field validation.

This test file ensures that Todo.from_dict validates text content for:
- Embedded NUL characters ('\x00')
- Excessive length (default max 10000 characters)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_null_byte_in_text() -> None:
    """Todo.from_dict should reject text containing NUL character."""
    data = {"id": 1, "text": "buy\x00milk", "done": False}

    with pytest.raises(ValueError, match=r"text.*NUL|text.*null.*byte|\\x00"):
        Todo.from_dict(data)


def test_from_dict_rejects_null_byte_at_start() -> None:
    """Todo.from_dict should reject text starting with NUL character."""
    data = {"id": 1, "text": "\x00valid text", "done": False}

    with pytest.raises(ValueError, match=r"text.*NUL|text.*null.*byte|\\x00"):
        Todo.from_dict(data)


def test_from_dict_rejects_null_byte_at_end() -> None:
    """Todo.from_dict should reject text ending with NUL character."""
    data = {"id": 1, "text": "valid text\x00", "done": False}

    with pytest.raises(ValueError, match=r"text.*NUL|text.*null.*byte|\\x00"):
        Todo.from_dict(data)


def test_from_dict_rejects_excessive_length() -> None:
    """Todo.from_dict should reject text exceeding 10000 characters."""
    long_text = "a" * 10001
    data = {"id": 1, "text": long_text, "done": False}

    with pytest.raises(ValueError, match=r"text.*length|text.*too long"):
        Todo.from_dict(data)


def test_from_dict_accepts_max_length_text() -> None:
    """Todo.from_dict should accept text at exactly 10000 characters."""
    max_text = "a" * 10000
    data = {"id": 1, "text": max_text, "done": False}

    todo = Todo.from_dict(data)
    assert todo.text == max_text


def test_from_dict_accepts_normal_text() -> None:
    """Todo.from_dict should accept normal text without NUL characters."""
    data = {"id": 1, "text": "Buy milk and eggs", "done": False}

    todo = Todo.from_dict(data)
    assert todo.text == "Buy milk and eggs"


def test_from_dict_accepts_unicode_text() -> None:
    """Todo.from_dict should accept unicode text without NUL characters."""
    data = {"id": 1, "text": "Buy café and 日本語", "done": False}

    todo = Todo.from_dict(data)
    assert todo.text == "Buy café and 日本語"


def test_from_dict_empty_text_after_strip() -> None:
    """Todo.from_dict should accept empty text (validation happens elsewhere)."""
    data = {"id": 1, "text": "", "done": False}

    todo = Todo.from_dict(data)
    assert todo.text == ""
