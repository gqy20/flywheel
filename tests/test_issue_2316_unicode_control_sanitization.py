"""Regression tests for Issue #2316: Unicode bidirectional control character sanitization.

This test file ensures that Unicode bidirectional override characters and zero-width
characters are properly escaped to prevent text spoofing attacks.

Security: These control characters can be used to trick users about the actual
content of text (e.g., making "malicious.com" appear as "github.com").
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


def test_sanitize_text_escapes_rtl_override_u202e() -> None:
    """RTL override (U+202E) should be escaped to prevent text spoofing."""
    # U+202E RIGHT-TO-LEFT OVERRIDE
    result = _sanitize_text("test\u202eafter")
    # Should be escaped
    assert r"\u202e" in result.lower() or r"\u202e" in result
    # Should not contain actual RTL override character
    assert "\u202e" not in result


def test_sanitize_text_escapes_ltr_override_u202d() -> None:
    """LTR override (U+202D) should be escaped."""
    # U+202D LEFT-TO-RIGHT OVERRIDE
    result = _sanitize_text("test\u202dafter")
    # Should be escaped
    assert r"\u202d" in result.lower() or r"\u202d" in result
    assert "\u202d" not in result


def test_sanitize_text_escapes_zero_width_space_u200b() -> None:
    """Zero-width space (U+200B) should be escaped."""
    # U+200B ZERO WIDTH SPACE
    result = _sanitize_text("test\u200bafter")
    # Should be escaped
    assert r"\u200b" in result.lower() or r"\u200b" in result
    assert "\u200b" not in result


def test_sanitize_text_escapes_all_bidi_overrides() -> None:
    """All bidirectional override characters (U+202A-U+202E) should be escaped."""
    # U+202A LEFT-TO-RIGHT EMBEDDING
    assert r"\u202a" in _sanitize_text("a\u202ab").lower()
    # U+202B RIGHT-TO-LEFT EMBEDDING
    assert r"\u202b" in _sanitize_text("a\u202bb").lower()
    # U+202C POP DIRECTIONAL FORMAT
    assert r"\u202c" in _sanitize_text("a\u202cb").lower()
    # U+202D LEFT-TO-RIGHT OVERRIDE
    assert r"\u202d" in _sanitize_text("a\u202db").lower()
    # U+202E RIGHT-TO-LEFT OVERRIDE
    assert r"\u202e" in _sanitize_text("a\u202eb").lower()


def test_sanitize_text_escapes_zero_width_chars() -> None:
    """Zero-width characters (U+200B-U+200D) should be escaped."""
    # U+200B ZERO WIDTH SPACE
    assert r"\u200b" in _sanitize_text("a\u200bb").lower()
    # U+200C ZERO WIDTH NON-JOINER
    assert r"\u200c" in _sanitize_text("a\u200cb").lower()
    # U+200D ZERO WIDTH JOINER
    assert r"\u200d" in _sanitize_text("a\u200db").lower()


def test_sanitize_text_preserves_normal_arabic_text() -> None:
    """Normal Arabic/Hebrew text should NOT be escaped."""
    # Arabic text - should pass through unchanged
    arabic = "مرحبا"
    assert _sanitize_text(arabic) == arabic

    # Hebrew text - should pass through unchanged
    hebrew = "שלום"
    assert _sanitize_text(hebrew) == hebrew


def test_sanitize_text_preserves_normal_unicode() -> None:
    """Normal Unicode characters should NOT be escaped."""
    # Emoji
    assert _sanitize_text("Hello 🎉") == "Hello 🎉"
    # Chinese
    assert _sanitize_text("你好") == "你好"
    # Japanese
    assert _sanitize_text("こんにちは") == "こんにちは"


def test_format_todo_escapes_bidi_overrides() -> None:
    """TodoFormatter should escape bidirectional override characters."""
    todo = Todo(id=1, text="github.com\u202e@moc.ebutuoc.liam", done=False)
    result = TodoFormatter.format_todo(todo)
    # Should be escaped, not raw
    assert r"\u202e" in result.lower()
    assert "\u202e" not in result


def test_format_todo_escapes_zero_width_spaces() -> None:
    """TodoFormatter should escape zero-width characters."""
    todo = Todo(id=1, text="Buy\u200bmilk", done=False)
    result = TodoFormatter.format_todo(todo)
    # Should be escaped
    assert r"\u200b" in result.lower()
    assert "\u200b" not in result


def test_sanitize_text_mixed_controls_and_bidi() -> None:
    """Both ASCII control chars and bidi overrides should be escaped."""
    # Mix of newline (C0) and RTL override (Unicode bidi)
    result = _sanitize_text("before\nmid\u202eend")
    assert "\\n" in result
    assert r"\u202e" in result.lower()
    assert "\n" not in result
    assert "\u202e" not in result
