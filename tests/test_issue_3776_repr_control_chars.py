"""Tests for Todo.__repr__ control character sanitization (Issue #3776).

These tests verify that __repr__ properly escapes/sanitizes control characters
to prevent terminal output manipulation and ensure debug-friendly output.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_sanitize_null_byte() -> None:
    """repr should not contain literal null bytes."""
    todo = Todo(id=1, text="test\x00value")
    result = repr(todo)

    # Should NOT contain literal null byte
    assert "\x00" not in result
    # Should contain escaped representation
    assert "\\x00" in result


def test_repr_sanitize_control_characters() -> None:
    """repr should escape control characters (0x00-0x1f)."""
    todo = Todo(id=1, text="test\x01\x02\x03value")
    result = repr(todo)

    # Should NOT contain literal control characters
    assert "\x01" not in result
    assert "\x02" not in result
    assert "\x03" not in result
    # Should contain escaped representations
    assert "\\x01" in result
    assert "\\x02" in result
    assert "\\x03" in result


def test_repr_sanitize_ansi_escape() -> None:
    """repr should escape ANSI escape sequences (0x1b)."""
    todo = Todo(id=1, text="test\x1b[31mred\x1b[0m")
    result = repr(todo)

    # Should NOT contain literal escape character
    assert "\x1b" not in result
    # Should contain escaped representation
    assert "\\x1b" in result


def test_repr_sanitize_del_character() -> None:
    """repr should escape DEL character (0x7f)."""
    todo = Todo(id=1, text="test\x7fvalue")
    result = repr(todo)

    # Should NOT contain literal DEL character
    assert "\x7f" not in result
    # Should contain escaped representation
    assert "\\x7f" in result


def test_repr_sanitize_c1_control_characters() -> None:
    """repr should escape C1 control characters (0x80-0x9f)."""
    todo = Todo(id=1, text="test\x80\x9fvalue")
    result = repr(todo)

    # Should NOT contain literal C1 control characters
    assert "\x80" not in result
    assert "\x9f" not in result
    # Should contain escaped representations
    assert "\\x80" in result
    assert "\\x9f" in result


def test_repr_preserves_newlines_as_escaped() -> None:
    """repr should escape newlines as \\n, not literal newlines."""
    todo = Todo(id=1, text="line1\nline2")
    result = repr(todo)

    # Should NOT contain literal newline
    assert "\n" not in result
    # Should contain escaped newline representation
    assert "\\n" in result


def test_repr_preserves_tabs_as_escaped() -> None:
    """repr should escape tabs as \\t, not literal tabs."""
    todo = Todo(id=1, text="col1\tcol2")
    result = repr(todo)

    # Should NOT contain literal tab
    assert "\t" not in result
    # Should contain escaped tab representation
    assert "\\t" in result


def test_repr_preserves_carriage_return_as_escaped() -> None:
    """repr should escape carriage returns as \\r, not literal CR."""
    todo = Todo(id=1, text="line1\rline2")
    result = repr(todo)

    # Should NOT contain literal carriage return
    assert "\r" not in result
    # Should contain escaped representation
    assert "\\r" in result


def test_repr_output_is_printable_ascii() -> None:
    """repr output should be printable ASCII or properly escaped Unicode."""
    todo = Todo(id=1, text="test\x00\x01\x1b\x7f\x80")
    result = repr(todo)

    # All characters in repr output should be printable
    # (ASCII 0x20-0x7e, or escaped sequences, or valid Unicode)
    for char in result:
        code = ord(char)
        # Allow printable ASCII, backslash, and any valid Unicode above 0x9f
        assert (
            0x20 <= code <= 0x7E  # Printable ASCII
            or code > 0x9F  # Valid Unicode above C1 controls
        ), f"Non-printable character in repr: {char!r} (code {code})"


def test_repr_complex_mixed_control_chars() -> None:
    """repr should handle complex text with multiple control character types."""
    # Mix of null, control chars, ANSI escape, DEL, and C1
    text = "start\x00\x01\x1b[31m\x7f\x80end"
    todo = Todo(id=1, text=text)
    result = repr(todo)

    # Should NOT contain any literal control characters
    for code in range(0x00, 0x20):
        assert chr(code) not in result, f"Found control char \\x{code:02x}"
    for code in range(0x7F, 0xA0):
        assert chr(code) not in result, f"Found control char \\x{code:02x}"
