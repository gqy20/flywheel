"""Regression tests for Issue #2400: Unicode bidi control character sanitization.

This test file ensures that Unicode bidirectional control characters
(U+202A-U+202E, U+2066-U+2069) are properly escaped to prevent
trojan source spoofing attacks.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


def test_sanitize_text_escapes_rlo_u202e() -> None:
    """U+202E (RIGHT-TO-LEFT OVERRIDE) should be escaped to \\u202e."""
    # The classic trojan source attack character
    result = _sanitize_text("hello\u202eTROLL")
    assert result == r"hello\u202eTROLL"
    # Should not contain actual RLO character
    assert "\u202e" not in result


def test_sanitize_text_escapes_lro_u202d() -> None:
    """U+202D (LEFT-TO-RIGHT OVERRIDE) should be escaped to \\u202d."""
    result = _sanitize_text("before\u202dAFTER")
    assert result == r"before\u202dAFTER"
    assert "\u202d" not in result


def test_sanitize_text_escapes_all_bidi_override_chars() -> None:
    """All bidi override chars U+202A-U+202E should be escaped."""
    # LRE - Left-to-Right Embedding
    assert _sanitize_text("test\u202a") == r"test\u202a"
    # RLE - Right-to-Left Embedding
    assert _sanitize_text("test\u202b") == r"test\u202b"
    # PDF - Pop Directional Format
    assert _sanitize_text("test\u202c") == r"test\u202c"
    # LRO - Left-to-Right Override
    assert _sanitize_text("test\u202d") == r"test\u202d"
    # RLO - Right-to-Left Override
    assert _sanitize_text("test\u202e") == r"test\u202e"


def test_sanitize_text_escapes_all_bidi_isolate_chars() -> None:
    """All bidi isolate chars U+2066-U+2069 should be escaped."""
    # LRI - Left-to-Right Isolate
    assert _sanitize_text("test\u2066") == r"test\u2066"
    # RLI - Right-to-Left Isolate
    assert _sanitize_text("test\u2067") == r"test\u2067"
    # FSI - First Strong Isolate
    assert _sanitize_text("test\u2068") == r"test\u2068"
    # PDI - Pop Directional Isolate
    assert _sanitize_text("test\u2069") == r"test\u2069"


def test_sanitize_text_mixed_bidi_and_normal_text() -> None:
    """Bidi chars should be escaped even when mixed with normal text."""
    result = _sanitize_text("normal \u202e REVERSED text")
    assert result == r"normal \u202e REVERSED text"
    assert "\u202e" not in result


def test_sanitize_text_multiple_bidi_chars() -> None:
    """Multiple bidi control characters should all be escaped."""
    result = _sanitize_text("\u202a\u202b\u202c\u202d\u202e")
    assert result == r"\u202a\u202b\u202c\u202d\u202e"


def test_sanitize_text_normal_unicode_passes_through() -> None:
    """Normal Unicode text (Chinese, Japanese, emojis) should pass unchanged."""
    # Chinese
    assert _sanitize_text("你好世界") == "你好世界"
    # Japanese
    assert _sanitize_text("こんにちは") == "こんにちは"
    # Korean
    assert _sanitize_text("안녕하세요") == "안녕하세요"
    # Emojis
    assert _sanitize_text("🎉🚀✅") == "🎉🚀✅"
    # Arabic (RTL language, but not a control char - should pass)
    assert _sanitize_text("مرحبا") == "مرحبا"
    # Hebrew (RTL language, but not a control char - should pass)
    assert _sanitize_text("שלום") == "שלום"


def test_format_todo_escapes_bidi_chars() -> None:
    """TodoFormatter should escape bidi control characters in todo text."""
    todo = Todo(id=1, text="Buy milk\u202e[ ] FAKE_TODO", done=False)
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\u202e" in result
    # Should not contain actual bidi character
    assert "\u202e" not in result
    # Expected format
    assert result == r"[ ]   1 Buy milk\u202e[ ] FAKE_TODO"


def test_format_list_escapes_bidi_chars_in_multiple_todos() -> None:
    """format_list should escape bidi chars in all todos."""
    todos = [
        Todo(id=1, text="Normal task", done=False),
        Todo(id=2, text="Trojan\u202e task", done=True),
        Todo(id=3, text="Another normal", done=False),
    ]
    result = TodoFormatter.format_list(todos)
    # First todo unchanged
    assert "[ ]   1 Normal task" in result
    # Second todo has bidi escaped
    assert r"\u202e" in result
    # No actual bidi chars in output
    assert "\u202e" not in result


def test_sanitize_text_bidi_with_existing_control_chars() -> None:
    """Bidi chars should be escaped alongside existing control character sanitization."""
    # Mix of C0, C1, DEL, and bidi
    result = _sanitize_text("\x01\u202e\x7f\x9f")
    assert "\\x01" in result
    assert r"\u202e" in result
    assert "\\x7f" in result
    assert "\\x9f" in result
    # No actual control chars
    assert "\x01" not in result
    assert "\u202e" not in result
    assert "\x7f" not in result
    assert "\x9f" not in result
