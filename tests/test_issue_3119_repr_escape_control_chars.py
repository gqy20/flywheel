"""Tests for Todo.__repr__ escaping control characters (Issue #3119).

These tests verify that __repr__ escapes control characters like newlines,
carriage returns, and tabs so that repr output is always a single line.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_escapes_newlines() -> None:
    """repr(Todo) should escape newlines to prevent multi-line output."""
    todo = Todo(id=1, text="line1\nline2")
    result = repr(todo)

    # Should NOT contain a literal newline character
    assert "\n" not in result, f"repr should not contain literal newline: {result!r}"

    # Should contain escaped newline representation
    assert "\\n" in result, f"repr should contain escaped newline: {result!r}"


def test_repr_escapes_carriage_returns() -> None:
    """repr(Todo) should escape carriage returns."""
    todo = Todo(id=1, text="text\rwith\rcarriage")
    result = repr(todo)

    # Should NOT contain a literal carriage return
    assert "\r" not in result, f"repr should not contain literal CR: {result!r}"

    # Should contain escaped CR representation
    assert "\\r" in result, f"repr should contain escaped CR: {result!r}"


def test_repr_escapes_tabs() -> None:
    """repr(Todo) should escape tabs."""
    todo = Todo(id=1, text="col1\tcol2")
    result = repr(todo)

    # Should NOT contain a literal tab
    assert "\t" not in result, f"repr should not contain literal tab: {result!r}"

    # Should contain escaped tab representation
    assert "\\t" in result, f"repr should contain escaped tab: {result!r}"


def test_repr_is_single_line() -> None:
    """repr(Todo) should always be a single line even with control chars."""
    todo = Todo(id=1, text="a\nb\rc\td")
    result = repr(todo)

    # Count newlines in the result - should be 0
    newline_count = result.count("\n")
    assert newline_count == 0, f"repr should be single line, found {newline_count} newlines: {result!r}"


def test_repr_handles_multiple_newlines() -> None:
    """repr(Todo) should handle text with multiple newlines."""
    todo = Todo(id=1, text="line1\nline2\nline3\nline4")
    result = repr(todo)

    # Should be single line
    assert "\n" not in result
    # Should have all newlines escaped
    assert result.count("\\n") == 3, f"Expected 3 escaped newlines: {result!r}"


def test_repr_escapes_backslashes_correctly() -> None:
    """repr(Todo) should handle backslashes without double-escaping."""
    # Text with backslash followed by n (literal backslash-n, not newline)
    todo = Todo(id=1, text="path\\to\\file")
    result = repr(todo)

    # Should contain the backslashes (properly escaped in repr)
    assert "path" in result and "to" in result and "file" in result


def test_repr_with_newlines_and_truncation() -> None:
    """repr(Todo) should escape newlines even when text is truncated."""
    # Create text longer than 50 chars with embedded newlines
    long_text = "a" * 20 + "\n" + "b" * 20 + "\n" + "c" * 20
    todo = Todo(id=1, text=long_text)
    result = repr(todo)

    # Should be single line
    assert "\n" not in result, f"repr should be single line: {result!r}"


def test_repr_length_predictable_with_control_chars() -> None:
    """repr output length should be predictable even with control characters."""
    # Control chars get escaped, increasing length predictably
    todo = Todo(id=1, text="\n\t\r")  # 3 control chars
    result = repr(todo)

    # Each control char becomes 2-char escape (\n, \t, \r)
    # So escaped text should be 6 chars instead of 3
    # repr should be single line and reasonable length
    assert len(result) < 200, f"repr too long: {len(result)} chars"
    assert "\n" not in result
