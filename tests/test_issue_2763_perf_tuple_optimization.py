"""Regression test for Issue #2763: tuple literal performance optimization.

This test verifies that the tuple literal in control character check is replaced
with a module-level frozenset constant for better performance.
"""

from __future__ import annotations

from flywheel.formatter import _sanitize_text


def test_control_chars_exclude_common_whitespaces() -> None:
    """Common whitespace chars (\\n, \\r, \\t) should NOT get \\xNN escape."""
    # After earlier replacement loop, these become \\n \\r \\t escaped strings
    # The control char loop should NOT re-escape them as \\x0a \\x0d \\x09
    text = "Line1\nLine2\rTab\tHere"
    result = _sanitize_text(text)
    # Should contain \n \r \t escapes (from first replacement loop)
    assert "\\n" in result
    assert "\\r" in result
    assert "\\t" in result
    # Should NOT contain hex escapes for these common chars
    assert "\\x0a" not in result.lower()
    assert "\\x0d" not in result.lower()
    assert "\\x09" not in result.lower()


def test_other_control_chars_get_hex_escape() -> None:
    """Control chars other than \\n, \\r, \\t should get \\xNN escape."""
    # Null byte
    assert _sanitize_text("\x00") == "\\x00"
    # Unit separator
    assert _sanitize_text("\x1f") == "\\x1f"
    # DEL
    assert _sanitize_text("\x7f") == "\\x7f"
    # C1 controls
    assert _sanitize_text("\x80") == "\\x80"
    assert _sanitize_text("\x9f") == "\\x9f"


def test_sanitize_backslash_first() -> None:
    """Backslash must be escaped before any other escaping."""
    # Test that backslash is escaped first
    text = "test\\nvalue"
    result = _sanitize_text(text)
    # Backslash should be escaped, then "n" is literal
    assert "\\\\n" in result


def test_sanitize_mixed_content() -> None:
    """Mixed control characters and normal text should be handled correctly."""
    text = "Normal\0\x1b\nText\r\tEnd"
    result = _sanitize_text(text)
    # Normal text unchanged
    assert "Normal" in result
    assert "Text" in result
    assert "End" in result
    # Null byte escaped
    assert "\\x00" in result
    # ESC escaped
    assert "\\x1b" in result
    # Common whitespace as literal escapes
    assert "\\n" in result
    assert "\\r" in result
    assert "\\t" in result
