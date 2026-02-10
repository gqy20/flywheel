"""Regression tests for Issue #2400: Unicode bidirectional control character sanitization.

This test file ensures that Unicode bidirectional control characters
(U+202A-U+202E, U+2066-U+2069) are properly escaped to prevent
trojan source spoofing attacks.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


def test_sanitize_text_escapes_u202a_lre() -> None:
    """U+202A LEFT-TO-RIGHT EMBEDDING should be escaped."""
    # LRE (U+202A)
    text = "hello\u202aworld"
    result = _sanitize_text(text)
    assert result == r"hello\u202aworld"
    assert "\u202a" not in result


def test_sanitize_text_escapes_u202b_rle() -> None:
    """U+202B RIGHT-TO-LEFT EMBEDDING should be escaped."""
    # RLE (U+202B)
    text = "hello\u202bworld"
    result = _sanitize_text(text)
    assert result == r"hello\u202bworld"
    assert "\u202b" not in result


def test_sanitize_text_escapes_u202c_pdf() -> None:
    """U+202C POP DIRECTIONAL FORMAT should be escaped."""
    # PDF (U+202C)
    text = "hello\u202cworld"
    result = _sanitize_text(text)
    assert result == r"hello\u202cworld"
    assert "\u202c" not in result


def test_sanitize_text_escapes_u202d_lro() -> None:
    """U+202D LEFT-TO-RIGHT OVERRIDE should be escaped."""
    # LRO (U+202D)
    text = "hello\u202dworld"
    result = _sanitize_text(text)
    assert result == r"hello\u202dworld"
    assert "\u202d" not in result


def test_sanitize_text_escapes_u202e_rlo() -> None:
    """U+202E RIGHT-TO-LEFT OVERRIDE should be escaped."""
    # RLO (U+202E) - commonly used in trojan source attacks
    text = "hello\u202etroll"
    result = _sanitize_text(text)
    assert result == r"hello\u202etroll"
    assert "\u202e" not in result


def test_sanitize_text_escapes_u2066_lri() -> None:
    """U+2066 LEFT-TO-RIGHT ISOLATE should be escaped."""
    # LRI (U+2066)
    text = "hello\u2066world"
    result = _sanitize_text(text)
    assert result == r"hello\u2066world"
    assert "\u2066" not in result


def test_sanitize_text_escapes_u2067_rli() -> None:
    """U+2067 RIGHT-TO-LEFT ISOLATE should be escaped."""
    # RLI (U+2067)
    text = "hello\u2067world"
    result = _sanitize_text(text)
    assert result == r"hello\u2067world"
    assert "\u2067" not in result


def test_sanitize_text_escapes_u2068_fsi() -> None:
    """U+2068 FIRST STRONG ISOLATE should be escaped."""
    # FSI (U+2068)
    text = "hello\u2068world"
    result = _sanitize_text(text)
    assert result == r"hello\u2068world"
    assert "\u2068" not in result


def test_sanitize_text_escapes_u2069_pdi() -> None:
    """U+2069 POP DIRECTIONAL ISOLATE should be escaped."""
    # PDI (U+2069)
    text = "hello\u2069world"
    result = _sanitize_text(text)
    assert result == r"hello\u2069world"
    assert "\u2069" not in result


def test_sanitize_text_mixed_bidi_chars() -> None:
    """Multiple bidi control characters should all be escaped."""
    text = "a\u202ab\u202ec\u2066d"
    result = _sanitize_text(text)
    assert result == r"a\u202ab\u202ec\u2066d"
    assert "\u202a" not in result
    assert "\u202e" not in result
    assert "\u2066" not in result


def test_sanitize_text_normal_unicode_passes_through() -> None:
    """Normal Unicode text should pass through unchanged."""
    # Chinese characters
    assert _sanitize_text("你好") == "你好"
    # Japanese characters
    assert _sanitize_text("こんにちは") == "こんにちは"
    # Emojis
    assert _sanitize_text("🎉") == "🎉"
    # Arabic (RTL language - should pass through, bidi controls are the issue)
    assert _sanitize_text("مرحبا") == "مرحبا"
    # Hebrew (RTL language)
    assert _sanitize_text("שלום") == "שלום"


def test_sanitize_text_bidi_with_normal_unicode() -> None:
    """Bidi controls should be escaped even in mixed Unicode text."""
    # Chinese text with bidi override
    text = "你好\u202eworld"
    result = _sanitize_text(text)
    assert result == r"你好\u202eworld"
    assert "你好" in result  # Normal Chinese should pass through
    assert "\u202e" not in result  # Bidi control should be escaped


def test_format_todo_escapes_bidi_controls() -> None:
    """Todo with bidi control characters should be escaped."""
    todo = Todo(id=1, text="Buy milk\u202eTROLL", done=False)
    result = TodoFormatter.format_todo(todo)
    assert r"\u202e" in result
    assert "\u202e" not in result


def test_format_todo_preserves_normal_unicode() -> None:
    """Normal Unicode in todos should be preserved."""
    todo = Todo(id=1, text="Buy milk and 你好", done=False)
    result = TodoFormatter.format_todo(todo)
    assert "你好" in result
