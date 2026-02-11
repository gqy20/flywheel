"""Regression tests for Issue #2841: __repr__ control character escaping.

This test file ensures that control characters in todo.text are properly escaped
in __repr__ to prevent terminal output manipulation via debugger/repr.

The fix applies _sanitize_text() (from formatter.py) to __repr__ for consistency
with the CLI formatter and defense-in-depth security.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_escapes_newline() -> None:
    """repr(Todo) should escape newlines to prevent line breaking in debug output."""
    todo = Todo(id=1, text="test\nFAKE")
    result = repr(todo)

    # Should not contain actual newline character
    assert "\n" not in result, f"repr output should not contain literal newline: {result!r}"
    # Should be single-line output
    assert result.count("\n") == 0, "repr should be single-line"


def test_repr_escapes_carriage_return() -> None:
    """repr(Todo) should escape carriage returns."""
    todo = Todo(id=1, text="test\rFAKE")
    result = repr(todo)

    assert "\r" not in result, f"repr output should not contain literal CR: {result!r}"


def test_repr_escapes_tab() -> None:
    """repr(Todo) should escape tabs."""
    todo = Todo(id=1, text="test\tFAKE")
    result = repr(todo)

    assert "\t" not in result, f"repr output should not contain literal tab: {result!r}"


def test_repr_escapes_ansi_escape_codes() -> None:
    """repr(Todo) should escape ANSI escape sequences to prevent terminal injection."""
    todo = Todo(id=1, text="\x1b[31mRED\x1b[0m")
    result = repr(todo)

    # Should not contain actual ESC character (0x1b)
    assert "\x1b" not in result, f"repr output should not contain literal ESC: {result!r}"


def test_repr_escapes_null_byte() -> None:
    """repr(Todo) should escape null bytes."""
    todo = Todo(id=1, text="test\x00FAKE")
    result = repr(todo)

    assert "\x00" not in result, f"repr output should not contain literal null byte: {result!r}"


def test_repr_escapes_del_byte() -> None:
    """repr(Todo) should escape DEL byte (0x7f)."""
    todo = Todo(id=1, text="test\x7fFAKE")
    result = repr(todo)

    assert "\x7f" not in result, f"repr output should not contain literal DEL: {result!r}"


def test_repr_escapes_c1_control_chars() -> None:
    """repr(Todo) should escape C1 control characters (0x80-0x9f)."""
    todo = Todo(id=1, text="test\x9bFAKE")  # CSI (0x9b)
    result = repr(todo)

    assert "\x9b" not in result, f"repr output should not contain literal C1: {result!r}"


def test_repr_normal_text_readable() -> None:
    """Normal todo text without control characters should remain readable."""
    todo = Todo(id=1, text="Buy groceries")
    result = repr(todo)

    assert "Buy groceries" in result
    assert "Todo" in result
    assert "id=1" in result


def test_repr_with_unicode() -> None:
    """Unicode characters should pass through unchanged."""
    todo = Todo(id=1, text="Buy café and 日本語")
    result = repr(todo)

    assert "café" in result
    assert "日本語" in result


def test_repr_truncation_with_control_chars() -> None:
    """Long text with control chars should be truncated safely."""
    # Text > 50 chars with control char near truncation boundary (position 47)
    long_text = "a" * 47 + "\nFAKE"
    todo = Todo(id=1, text=long_text)
    result = repr(todo)

    # Should be truncated (contain ...)
    assert "..." in result
    # Should not contain actual control characters even after truncation
    assert "\n" not in result, f"repr contains literal newline after truncation: {result!r}"


def test_repr_output_is_single_line() -> None:
    """repr output should always be single-line for debugger usability."""
    todo = Todo(id=1, text="line1\nline2\rline3\tline4")
    result = repr(todo)

    # Should not contain any actual newlines
    newline_count = result.count("\n")
    assert newline_count == 0, f"repr output should be single-line, found {newline_count} newlines: {result!r}"


def test_repr_multiple_control_chars() -> None:
    """repr with multiple different control chars should escape all of them."""
    todo = Todo(id=1, text="\n\r\t\x1b\x00\x7f")
    result = repr(todo)

    # No literal control characters in output
    for char in ["\n", "\r", "\t", "\x1b", "\x00", "\x7f"]:
        assert char not in result, f"repr should not contain literal {char!r}"
