"""Tests for Todo.__repr__ control character sanitization (Issue #3255).

These tests verify that:
1. ANSI escape sequences are escaped in __repr__ output
2. Other control characters are escaped in __repr__ output
3. The repr output does not produce unexpected terminal effects
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_escapes_ansi_sequences() -> None:
    """__repr__ should escape ANSI escape sequences, not include them literally."""
    # Text containing ANSI escape sequence for red color
    todo = Todo(id=1, text="a\x1b[31mRed\x1b[0mb")
    result = repr(todo)

    # The ESC character (0x1b) should be escaped, not present literally
    assert "\x1b" not in result, f"ANSI escape sequence not escaped in repr: {result!r}"

    # Should still contain the text identifier
    assert "Todo" in result
    assert "id=1" in result


def test_repr_escapes_newlines() -> None:
    """__repr__ should escape newlines to keep output on single line."""
    todo = Todo(id=1, text="line1\nline2")
    result = repr(todo)

    # No literal newlines in repr output
    assert "\n" not in result, f"Literal newline found in repr: {result!r}"

    # The newline should be escaped as \\n (backslash-n)
    assert "\\n" in result, f"Escaped newline not found in repr: {result!r}"
    assert "Todo" in result


def test_repr_escapes_carriage_returns() -> None:
    """__repr__ should escape carriage returns."""
    todo = Todo(id=1, text="text\rwith\rCRs")
    result = repr(todo)

    # No literal CR in repr output
    assert "\r" not in result, f"Literal CR found in repr: {result!r}"

    # The CR should be escaped
    assert "\\r" in result, f"Escaped CR not found in repr: {result!r}"


def test_repr_escapes_tab() -> None:
    """__repr__ should escape tab characters."""
    todo = Todo(id=1, text="text\twith\ttabs")
    result = repr(todo)

    # No literal tab in repr output
    assert "\t" not in result, f"Literal tab found in repr: {result!r}"

    # The tab should be escaped
    assert "\\t" in result, f"Escaped tab not found in repr: {result!r}"


def test_repr_escapes_bell() -> None:
    """__repr__ should escape bell character (BEL)."""
    todo = Todo(id=1, text="text\x07with\x07bell")
    result = repr(todo)

    # No literal BEL in repr output
    assert "\x07" not in result, f"Literal BEL found in repr: {result!r}"

    # Should still contain text identifier
    assert "Todo" in result


def test_repr_escapes_del_character() -> None:
    """__repr__ should escape DEL character (0x7f)."""
    todo = Todo(id=1, text="text\x7fwith\x7fDEL")
    result = repr(todo)

    # No literal DEL in repr output
    assert "\x7f" not in result, f"Literal DEL found in repr: {result!r}"

    # Should still contain text identifier
    assert "Todo" in result


def test_repr_single_line_output() -> None:
    """__repr__ output should be on a single line regardless of text content."""
    todo = Todo(id=1, text="line1\nline2\rline3")
    result = repr(todo)

    # Count newlines in the result - should be 0
    newline_count = result.count("\n")
    assert newline_count == 0, f"repr output has {newline_count} newlines: {result!r}"
