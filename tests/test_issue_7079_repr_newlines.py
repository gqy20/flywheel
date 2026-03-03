"""Tests for Todo.__repr__ newline escaping (Issue #7079).

These tests verify that Todo.__repr__ produces single-line output even when
the text contains newline characters or other control characters that could
break debugger display and log parsing.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_no_literal_newline_in_output() -> None:
    """repr(Todo) with newline in text should not contain literal newline."""
    todo = Todo(id=1, text="line1\nline2")
    result = repr(todo)

    # The repr output must NOT contain literal newline characters
    assert "\n" not in result, (
        f"repr should escape newlines, but got literal newline in: {result!r}"
    )


def test_repr_is_single_line() -> None:
    """repr(Todo) output must be a single line for debugger compatibility."""
    todo = Todo(id=1, text="a\nb\nc\nd")
    result = repr(todo)

    # Count lines - should be exactly 1
    lines = result.split("\n")
    assert len(lines) == 1, (
        f"repr should be single line, but got {len(lines)} lines: {result!r}"
    )


def test_repr_escapes_various_control_chars() -> None:
    """repr(Todo) should escape all control characters that could break output."""
    test_cases = [
        ("newline", "a\nb"),
        ("carriage return", "a\rb"),
        ("tab", "a\tb"),
        ("CRLF", "a\r\nb"),
        ("vertical tab", "a\x0bb"),
        ("form feed", "a\fb"),
        ("mixed", "a\n\t\r\b"),
    ]

    for name, text in test_cases:
        todo = Todo(id=1, text=text)
        result = repr(todo)

        # No literal newlines in output
        assert "\n" not in result, f"{name}: repr contains literal newline: {result!r}"
        # No literal carriage returns in output
        assert "\r" not in result, f"{name}: repr contains literal CR: {result!r}"


def test_repr_with_truncated_text_containing_newline() -> None:
    """repr(Todo) should escape newlines even when text is truncated."""
    # Text longer than 50 chars with newline near truncation boundary
    long_text = "a" * 48 + "\n" + "more text here"
    todo = Todo(id=1, text=long_text)
    result = repr(todo)

    # Should be truncated but still no literal newlines
    assert "\n" not in result, (
        f"repr of truncated text contains literal newline: {result!r}"
    )
    assert "..." in result, "Long text should be truncated with ellipsis"


def test_repr_acceptance_criteria() -> None:
    """Verify exact acceptance criteria from issue #7079."""
    # Criteria 1: Todo with newline in text has single-line repr output
    todo = Todo(id=1, text="a\nb")
    result = repr(todo)
    assert result.count("\n") == 0, "repr must be single-line"

    # Criteria 2: repr does not contain literal newline character
    assert "\n" not in result, "repr must not contain literal newline"
