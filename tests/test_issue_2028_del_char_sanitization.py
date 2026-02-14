"""Regression tests for Issue #2028: DEL character (0x7f) sanitization.

This test file ensures that DEL character (0x7f/127) is properly escaped
to prevent terminal output manipulation.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


def test_sanitize_text_escapes_del_char() -> None:
    """DEL character (0x7f) should be escaped to \\x7f."""
    result = _sanitize_text("Normal\x7fAfter")
    assert result == "Normal\\x7fAfter"
    # Should not contain actual DEL character
    assert "\x7f" not in result


def test_sanitize_text_just_del_char() -> None:
    """Just DEL character should be escaped."""
    result = _sanitize_text("\x7f")
    assert result == "\\x7f"
    assert "\x7f" not in result


def test_sanitize_text_multiple_del_chars() -> None:
    """Multiple DEL characters should all be escaped."""
    result = _sanitize_text("\x7f\x7f\x7f")
    assert result == "\\x7f\\x7f\\x7f"
    assert "\x7f" not in result


def test_format_todo_escapes_del_char_in_text() -> None:
    """Todo with DEL in text should output escaped representation."""
    todo = Todo(id=1, text="Buy milk\x7f[ ] FAKE_TODO")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\x7f" in result
    # Should not contain actual DEL character
    assert "\x7f" not in result
    # Expected format
    assert result == "[ ]    1 Buy milk\\x7f[ ] FAKE_TODO"


def test_sanitize_text_mixed_control_and_del() -> None:
    """DEL with other control characters should all be escaped."""
    result = _sanitize_text("Before\x1f\x7f\x00After")
    assert "\\x1f" in result
    assert "\\x7f" in result
    assert "\\x00" in result
    # No actual control chars
    assert "\x1f" not in result
    assert "\x7f" not in result
    assert "\x00" not in result
