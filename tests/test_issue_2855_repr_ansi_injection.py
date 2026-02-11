"""Regression tests for Issue #2855: __repr__ ANSI escape sequence injection.

This test file ensures that control characters in todo.text are properly escaped
in __repr__ output to prevent terminal manipulation when debugging.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_escapes_ansi_escape_sequence() -> None:
    """ANSI escape sequences should be escaped in __repr__ output."""
    todo = Todo(id=1, text="\x1b[31mRed Text\x1b[0m Normal")
    result = repr(todo)

    # Should contain escaped representation
    assert "\\x1b" in result, f"Expected escaped \\x1b in: {result!r}"
    # Should not contain actual ESC character (0x1b)
    assert "\x1b" not in result, f"Found literal ESC character in: {result!r}"


def test_repr_escapes_null_byte() -> None:
    """Null byte should be escaped in __repr__ output."""
    todo = Todo(id=1, text="Before\x00After")
    result = repr(todo)

    assert "\\x00" in result, f"Expected escaped \\x00 in: {result!r}"
    assert "\x00" not in result, f"Found literal null byte in: {result!r}"


def test_repr_escapes_del_character() -> None:
    """DEL character (0x7f) should be escaped in __repr__ output."""
    todo = Todo(id=1, text="Before\x7fAfter")
    result = repr(todo)

    assert "\\x7f" in result, f"Expected escaped \\x7f in: {result!r}"
    assert "\x7f" not in result, f"Found literal DEL character in: {result!r}"


def test_repr_escapes_c1_control_characters() -> None:
    """C1 control characters (0x80-0x9f) should be escaped in __repr__ output."""
    # Test a few C1 control characters
    todo = Todo(id=1, text="Before\x80\x9fAfter")
    result = repr(todo)

    assert "\\x80" in result, f"Expected escaped \\x80 in: {result!r}"
    assert "\\x9f" in result, f"Expected escaped \\x9f in: {result!r}"
    assert "\x80" not in result, f"Found literal C1 character in: {result!r}"
    assert "\x9f" not in result, f"Found literal C1 character in: {result!r}"


def test_repr_escapes_newline_carriage_return_tab() -> None:
    """Common control characters should be escaped in __repr__ output."""
    todo = Todo(id=1, text="Line1\nLine2\rTab\tHere")
    result = repr(todo)

    # Should contain escaped representations
    assert "\\n" in result, f"Expected escaped \\n in: {result!r}"
    assert "\\r" in result, f"Expected escaped \\r in: {result!r}"
    assert "\\t" in result, f"Expected escaped \\t in: {result!r}"

    # Should not contain actual control characters
    # Note: The repr string itself may have a newline for formatting, but the text field should be escaped
    # Check that the text portion is properly escaped
    assert "'Line1\\nLine2\\rTab\\tHere'" in result or '"Line1\\nLine2\\rTab\\tHere"' in result


def test_repr_normal_text_unchanged() -> None:
    """Normal todo text without control characters should work normally."""
    todo = Todo(id=1, text="Buy groceries")
    result = repr(todo)

    assert "Todo" in result
    assert "id=1" in result
    assert "Buy groceries" in result


def test_repr_with_unicode() -> None:
    """Unicode characters should pass through unchanged in __repr__ output."""
    todo = Todo(id=1, text="Buy café and 日本語")
    result = repr(todo)

    assert "café" in result
    assert "日本語" in result


def test_repr_with_ansi_in_truncated_text() -> None:
    """ANSI escapes should be escaped even in truncated text."""
    # Create text that will be truncated (over 50 chars)
    long_text = "\x1b[31m" + "a" * 50 + "dangerous"
    todo = Todo(id=1, text=long_text)
    result = repr(todo)

    # Should still escape the ANSI sequence
    assert "\\x1b" in result, f"Expected escaped \\x1b in truncated text: {result!r}"
    # Should not contain actual ESC character
    assert "\x1b" not in result, f"Found literal ESC in truncated text: {result!r}"
