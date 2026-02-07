"""Regression tests for Issue #2057: C1 control character (0x80-0x9f) sanitization.

This test file ensures that C1 control characters are properly escaped
to prevent UTF-8 terminal manipulation attacks.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


def test_sanitize_text_escapes_c1_control_chars() -> None:
    """C1 control characters (0x80-0x9f) should be escaped to \\xNN format."""
    # Test a few representative C1 control characters
    result = _sanitize_text("Normal\x80After")
    assert result == "Normal\\x80After"
    assert "\x80" not in result

    result = _sanitize_text("text\x9fend")
    assert result == "text\\x9fend"
    assert "\x9f" not in result

    # Test another in the middle of range
    result = _sanitize_text("start\x90middle")
    assert result == "start\\x90middle"
    assert "\x90" not in result


def test_sanitize_text_c1_boundary_chars() -> None:
    """Test exact boundaries of C1 range (0x80 and 0x9f)."""
    # Lower boundary (0x80)
    result = _sanitize_text("\x80")
    assert result == "\\x80"
    assert "\x80" not in result

    # Upper boundary (0x9f)
    result = _sanitize_text("\x9f")
    assert result == "\\x9f"
    assert "\x9f" not in result


def test_sanitize_text_unicode_unchanged() -> None:
    """Valid UTF-8 multi-byte characters should pass through unchanged."""
    # Japanese characters (multi-byte UTF-8)
    result = _sanitize_text("日本語")
    assert result == "日本語"

    # Accented characters
    result = _sanitize_text("café")
    assert result == "café"

    # Emoji
    result = _sanitize_text("Hello 😊 World")
    assert result == "Hello 😊 World"


def test_sanitize_text_multiple_c1_chars() -> None:
    """Multiple C1 control characters should all be escaped."""
    result = _sanitize_text("\x80\x90\x9f")
    assert result == "\\x80\\x90\\x9f"
    assert "\x80" not in result
    assert "\x90" not in result
    assert "\x9f" not in result


def test_sanitize_text_mixed_c0_and_c1() -> None:
    """C1 controls with C0 controls (0x00-0x1f) should all be escaped."""
    result = _sanitize_text("Before\x1f\x80\x9fAfter")
    assert "\\x1f" in result
    assert "\\x80" in result
    assert "\\x9f" in result
    # No actual control chars
    assert "\x1f" not in result
    assert "\x80" not in result
    assert "\x9f" not in result


def test_format_todo_escapes_c1_in_text() -> None:
    """Todo with C1 control characters in text should output escaped representation."""
    todo = Todo(id=1, text="Buy milk\x80[ ] FAKE_TODO")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\x80" in result
    # Should not contain actual C1 character
    assert "\x80" not in result
    # Expected format
    assert result == "[ ]   1 Buy milk\\x80[ ] FAKE_TODO"


def test_sanitize_text_char_before_c1_unchanged() -> None:
    """Character 0x7f (DEL) is escaped, but character 0x7e (~) should pass through."""
    result = _sanitize_text("~")
    assert result == "~"

    # Character 0xa0 (NO-BREAK SPACE) should pass through
    result = _sanitize_text("\xa0")
    assert result == "\xa0"
