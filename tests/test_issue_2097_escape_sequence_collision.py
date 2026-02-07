"""Regression tests for Issue #2097: Escape sequence collision.

The issue is that _sanitize_text() has a collision:
- Input '\x01' (actual control char) -> output '\x01'
- Input r'\x01' (literal backslash-x-zero-one) -> output '\x01'

This creates ambiguity. The fix is to escape backslashes first.
"""

from flywheel.formatter import _sanitize_text


def test_control_char_differs_from_literal_escape():
    """Actual control char and literal escape text must produce different outputs."""
    control_char_input = "\x01"  # Actual SOH control character (1 byte)
    literal_text_input = r"\x01"  # 6 characters: backslash, x, 0, 1

    control_output = _sanitize_text(control_char_input)
    literal_output = _sanitize_text(literal_text_input)

    # These must produce different outputs
    assert control_output != literal_output, (
        f"Collision detected: control char '\\x01' and literal text r'\\x01' "
        f"both produce '{control_output}'"
    )

    # Control character should be escaped as \x01
    assert control_output == r"\x01"

    # Literal text should have the backslash escaped first
    assert literal_output == r"\\x01"


def test_backslash_is_escaped():
    """Backslash character should be escaped to prevent ambiguity."""
    assert _sanitize_text("\\") == r"\\"


def test_mixed_backslash_and_control_chars():
    """Mixed backslashes and control chars should be distinguishable."""
    # Input: literal \n followed by actual newline
    result = _sanitize_text(r"\n" + "\n")

    # Should be: escaped backslash, literal n, escaped newline
    # r"\n" -> "\\n", "\n" -> "\n", total: "\\n\n"
    assert result == r"\\n\n"


def test_literal_backslash_x_remains_distinguishable():
    """Literal text looking like escape sequences should remain distinguishable."""
    # Multiple escape-looking patterns
    result = _sanitize_text(r"\x01\x02\n")

    # Backslash should be escaped, making each pattern distinguishable
    assert result == r"\\x01\\x02\\n"


def test_actual_control_chars_still_escaped():
    """Actual control characters must still be properly escaped."""
    # Mix of actual control characters
    result = _sanitize_text("\x00\x01\x1b\x7f")
    assert result == r"\x00\x01\x1b\x7f"


def test_complex_mixed_content():
    """Complex mix of literal backslashes and control characters."""
    # literal \ followed by actual control chars
    result = _sanitize_text("literal\\n\x01")

    # Backslash should be escaped, control char should be escaped
    assert result == r"literal\\n\x01"


def test_double_backslash_becomes_quad():
    """Double backslash should become escaped backslashes."""
    assert _sanitize_text(r"\\") == r"\\\\"
