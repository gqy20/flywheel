"""Regression tests for Issue #2316: Unicode bidirectional control character sanitization.

Unicode bidirectional control characters (U+202A-U+202E) and zero-width characters
(U+200B-U+200D) can be used for text spoofing attacks in terminal output. They should
be escaped to prevent confusion about actual todo content.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


def test_sanitize_text_escapes_rtl_override() -> None:
    """RTL override (U+202E) should be escaped to prevent text spoofing."""
    # U+202E is RIGHT-TO-LEFT OVERRIDE - forces text to render right-to-left
    # This can be used to make fake todos look real
    rtl_override = "\u202e"
    result = _sanitize_text(f"test{rtl_override}after")
    # Should be escaped as \\u202e or \\x202e
    assert "\\x202e" in result
    # Should not contain actual RTL override character
    assert "\u202e" not in result


def test_sanitize_text_escapes_ltr_override() -> None:
    """LTR override (U+202D) should be escaped."""
    ltr_override = "\u202d"
    result = _sanitize_text(f"before{ltr_override}test")
    assert "\\x202d" in result
    assert "\u202d" not in result


def test_sanitize_text_escapes_all_bidi_overrides() -> None:
    """All bidirectional override characters (U+202A-U+202E) should be escaped."""
    # U+202A: LEFT-TO-RIGHT EMBEDDING
    # U+202B: RIGHT-TO-LEFT EMBEDDING
    # U+202C: POP DIRECTIONAL FORMATTING
    # U+202D: LEFT-TO-RIGHT OVERRIDE
    # U+202E: RIGHT-TO-LEFT OVERRIDE
    for code in [0x202a, 0x202b, 0x202c, 0x202d, 0x202e]:
        char = chr(code)
        result = _sanitize_text(f"x{char}y")
        assert f"\\x{code:04x}" in result, f"U+{code:04X} not escaped"
        assert char not in result, f"U+{code:04X} still present in output"


def test_sanitize_text_escapes_zero_width_space() -> None:
    """Zero-width space (U+200B) should be escaped."""
    zero_width = "\u200b"
    result = _sanitize_text(f"before{zero_width}after")
    assert "\\x200b" in result
    assert "\u200b" not in result


def test_sanitize_text_escapes_all_zero_width_chars() -> None:
    """All zero-width characters (U+200B-U+200D) should be escaped."""
    # U+200B: ZERO WIDTH SPACE
    # U+200C: ZERO WIDTH NON-JOINER
    # U+200D: ZERO WIDTH JOINER
    for code in [0x200b, 0x200c, 0x200d]:
        char = chr(code)
        result = _sanitize_text(f"a{char}b")
        assert f"\\x{code:04x}" in result, f"U+{code:04X} not escaped"
        assert char not in result, f"U+{code:04X} still present in output"


def test_format_todo_escapes_rtl_spoofing() -> None:
    """Todo with RTL override should be escaped to prevent spoofing."""
    # This is a realistic attack: use RTL override to make fake text look real
    # The RTL override causes the text after it to render right-to-left
    todo = Todo(id=1, text="Buy milk\u202e[ ] FAKE_TODO", done=False)
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\x202e" in result
    # Should not contain actual RTL override
    assert "\u202e" not in result
    # Should be single line
    assert "\n" not in result


def test_format_todo_with_zero_width_spoofing() -> None:
    """Todo with zero-width characters should be visible when escaped."""
    # Zero-width characters can hide text or create confusion
    todo = Todo(id=1, text="Buy milk\u200b(milk is actually poisoned)", done=False)
    result = TodoFormatter.format_todo(todo)
    assert "\\x200b" in result
    assert "\u200b" not in result


def test_normal_arabic_text_passes_through() -> None:
    """Normal Arabic text should NOT be escaped - it's valid content."""
    # Arabic is naturally right-to-left but should pass through unchanged
    # Only the CONTROL characters should be escaped
    arabic = "شراء الحليب"  # "Buy milk" in Arabic
    result = _sanitize_text(arabic)
    assert result == arabic


def test_normal_hebrew_text_passes_through() -> None:
    """Normal Hebrew text should NOT be escaped - it's valid content."""
    hebrew = "קנה חלב"  # "Buy milk" in Hebrew
    result = _sanitize_text(hebrew)
    assert result == hebrew


def test_mixed_controls_and_valid_unicode() -> None:
    """Both control chars and valid Unicode should be handled correctly."""
    # Mix of bidi controls (should escape), Arabic (should pass), and Hebrew (should pass)
    text = "Test \u202e spoof\u200b شراء קנה"
    result = _sanitize_text(text)
    # Controls should be escaped
    assert "\\x202e" in result
    assert "\\x200b" in result
    # Valid Arabic/Hebrew should pass through
    assert "شراء" in result
    assert "קנה" in result
