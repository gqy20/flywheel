"""Regression tests for Issue #2057: C1 control character sanitization.

This test file ensures that C1 control characters (0x80-0x9f) are properly escaped
to prevent UTF-8 terminal manipulation attacks.

C1 control characters are a set of 32 control codes in the range 0x80-0x9f
that can potentially enable terminal manipulation in terminals that interpret them.
Key dangerous ones include:
- 0x9b (CSI - Control Sequence Introducer): ANSI escape sequences
- 0x9d (OSC - Operating System Command): Window title, clipboard manipulation
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


def test_sanitize_text_escapes_c1_range_start() -> None:
    """C1 control character 0x80 should be escaped to \\x80."""
    result = _sanitize_text("text\x80after")
    assert result == "text\\x80after"
    # Should not contain actual 0x80 character
    assert "\x80" not in result


def test_sanitize_text_escapes_c1_range_end() -> None:
    """C1 control character 0x9f should be escaped to \\x9f."""
    result = _sanitize_text("normal\x9fend")
    assert result == "normal\\x9fend"
    # Should not contain actual 0x9f character
    assert "\x9f" not in result


def test_sanitize_text_escapes_csi_char() -> None:
    """C1 CSI character (0x9b) should be escaped - dangerous ANSI escape code."""
    result = _sanitize_text("normal\x9b[31mRED[0m")
    assert "\\x9b" in result
    # Should not contain actual 0x9b character
    assert "\x9b" not in result


def test_sanitize_text_escapes_osc_char() -> None:
    """C1 OSC character (0x9d) should be escaped - can manipulate terminal state."""
    result = _sanitize_text("normal\x9d0;Title\x07")
    assert "\\x9d" in result
    # Should not contain actual 0x9d character
    assert "\x9d" not in result


def test_sanitize_text_just_c1_char() -> None:
    """Just C1 character should be escaped."""
    for code in [0x80, 0x85, 0x90, 0x95, 0x9a, 0x9f]:
        result = _sanitize_text(chr(code))
        assert result == f"\\x{code:02x}"
        assert chr(code) not in result


def test_sanitize_text_multiple_c1_chars() -> None:
    """Multiple C1 control characters should all be escaped."""
    result = _sanitize_text("\x80\x90\x9f")
    assert result == "\\x80\\x90\\x9f"
    assert "\x80" not in result
    assert "\x90" not in result
    assert "\x9f" not in result


def test_sanitize_text_c0_and_c1_mixed() -> None:
    """C0 and C1 control characters should all be escaped together."""
    result = _sanitize_text("Before\x1f\x80\x7f\x9fAfter")
    # All should be escaped
    assert "\\x1f" in result
    assert "\\x80" in result
    assert "\\x7f" in result
    assert "\\x9f" in result
    # No actual control chars
    assert "\x1f" not in result
    assert "\x80" not in result
    assert "\x7f" not in result
    assert "\x9f" not in result


def test_format_todo_escapes_c1_in_text() -> None:
    """Todo with C1 control characters in text should output escaped representation."""
    todo = Todo(id=1, text="Buy milk\x9b[31m[ ] FAKE_TODO")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\x9b" in result
    # Should not contain actual C1 character
    assert "\x9b" not in result
    # Expected format
    assert result == "[ ]   1 Buy milk\\x9b[31m[ ] FAKE_TODO"


def test_sanitize_text_unicode_unchanged() -> None:
    """Valid multi-byte UTF-8 Unicode text should pass through unchanged."""
    # Japanese
    result = _sanitize_text("日本語")
    assert result == "日本語"
    # Accented characters
    result = _sanitize_text("café")
    assert result == "café"
    # Emoji (multi-byte UTF-8)
    result = _sanitize_text("🎉")
    assert result == "🎉"
    # Chinese
    result = _sanitize_text("你好")
    assert result == "你好"


def test_sanitize_text_printable_ascii_unchanged() -> None:
    """Printable ASCII (0x20-0x7e) should pass through unchanged."""
    result = _sanitize_text("Hello World! @#$%")
    assert result == "Hello World! @#$%"


def test_sanitize_text_mixed_content() -> None:
    """Mixed normal text, Unicode, and C1 controls should handle correctly."""
    result = _sanitize_text("日本語\x80text")
    # C1 should be escaped, Unicode preserved
    assert "\\x80" in result
    assert "\x80" not in result
    assert "日本語" in result
    assert "text" in result
