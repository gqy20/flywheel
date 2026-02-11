"""Regression tests for Issue #2881: from_dict text field content validation.

This test file ensures that Todo.from_dict validates text content for:
1. Embedded NUL characters (\x00)
2. Excessive length (default max: 10000 chars)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_null_byte_in_text() -> None:
    """Todo.from_dict with text containing \\x00 should raise ValueError."""
    with pytest.raises(ValueError, match="NUL character"):
        Todo.from_dict({"id": 1, "text": "buy\x00milk"})


def test_from_dict_rejects_excessive_length_text() -> None:
    """Todo.from_dict with text length > 10000 should raise ValueError."""
    long_text = "a" * 10001
    with pytest.raises(ValueError, match="exceeds maximum length"):
        Todo.from_dict({"id": 1, "text": long_text})


def test_from_dict_accepts_max_length_text() -> None:
    """Todo.from_dict should accept text at exactly max length (10000)."""
    max_text = "a" * 10000
    todo = Todo.from_dict({"id": 1, "text": max_text})
    assert todo.text == max_text


def test_from_dict_rejects_null_byte_at_start() -> None:
    """Todo.from_dict should reject NUL byte at the start of text."""
    with pytest.raises(ValueError, match="NUL character"):
        Todo.from_dict({"id": 1, "text": "\x00start"})


def test_from_dict_rejects_null_byte_at_end() -> None:
    """Todo.from_dict should reject NUL byte at the end of text."""
    with pytest.raises(ValueError, match="NUL character"):
        Todo.from_dict({"id": 1, "text": "end\x00"})


def test_from_dict_rejects_multiple_null_bytes() -> None:
    """Todo.from_dict should reject multiple NUL bytes in text."""
    with pytest.raises(ValueError, match="NUL character"):
        Todo.from_dict({"id": 1, "text": "a\x00b\x00c"})


def test_from_dict_accepts_normal_text() -> None:
    """Todo.from_dict should accept normal text without NUL bytes."""
    todo = Todo.from_dict({"id": 1, "text": "Buy groceries"})
    assert todo.text == "Buy groceries"
