"""Tests for Todo.__repr__ newline escaping (Issue #7079).

This test explicitly verifies that __repr__ properly escapes newlines
and other control characters to ensure single-line output that works
correctly in debuggers and log parsing.

Note: Python's !r format specifier already handles this correctly by
escaping control characters. This test documents the expected behavior.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_escapes_newlines_no_literal_newline() -> None:
    """repr(Todo) must not contain literal newline characters."""
    todo = Todo(id=1, text="line1\nline2")
    result = repr(todo)

    # The repr output must be a single line - no literal newline chars
    assert "\n" not in result, (
        f"repr should not contain literal newlines: {result!r}"
    )


def test_repr_escapes_newlines_single_line_output() -> None:
    """repr(Todo) output must be single-line for debugger compatibility."""
    todo = Todo(id=1, text="line1\nline2\nline3")
    result = repr(todo)

    # Count actual newlines in the output
    line_count = result.count("\n")
    assert line_count == 0, (
        f"repr should be single line but has {line_count} newlines: {result!r}"
    )


def test_repr_escapes_carriage_return() -> None:
    """repr(Todo) must escape carriage returns."""
    todo = Todo(id=1, text="line1\r\nline2")
    result = repr(todo)

    assert "\r" not in result, f"repr should not contain literal CR: {result!r}"
    assert "\n" not in result, f"repr should not contain literal LF: {result!r}"


def test_repr_escapes_tab() -> None:
    """repr(Todo) must escape tab characters."""
    todo = Todo(id=1, text="col1\tcol2")
    result = repr(todo)

    assert "\t" not in result, f"repr should not contain literal tab: {result!r}"


def test_repr_newline_appears_as_escaped_sequence() -> None:
    """repr(Todo) should show newlines as backslash-n, not literal newlines."""
    todo = Todo(id=1, text="a\nb")
    result = repr(todo)

    # The string should contain the two-character escape sequence \n
    # (backslash followed by 'n'), not a literal newline
    assert "\\n" in result, (
        f"repr should contain escaped newline sequence '\\\\n': {result!r}"
    )


def test_repr_mixed_control_characters() -> None:
    """repr(Todo) must handle mixed control characters correctly."""
    todo = Todo(id=1, text="a\nb\tc\rd")
    result = repr(todo)

    # No literal control characters should appear
    assert "\n" not in result
    assert "\t" not in result
    assert "\r" not in result

    # Should appear as escaped sequences
    assert "\\n" in result
    assert "\\t" in result
    assert "\\r" in result


def test_repr_long_text_with_newline_stays_single_line() -> None:
    """Truncated text with newlines must still produce single-line repr."""
    # Create text longer than 50 chars that will be truncated
    long_text = "x" * 40 + "\n" + "y" * 40
    todo = Todo(id=1, text=long_text)
    result = repr(todo)

    # Even after truncation, no literal newlines
    assert "\n" not in result, f"Truncated repr should not have newlines: {result!r}"
