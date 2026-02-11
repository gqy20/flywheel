"""Regression tests for Issue #2841: __repr__ control character sanitization.

This test file ensures that control characters in todo.text are properly escaped
in __repr__() output to prevent terminal output manipulation via debugger/repr.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_escapes_newline_in_text() -> None:
    """repr(Todo) with \\n in text should output escaped newline, not actual newline."""
    todo = Todo(id=1, text="Buy milk\n[ ] FAKE_TODO")
    result = repr(todo)
    # Should contain escaped representation, not actual newline
    assert "\\n" in result
    # Should be single line (no actual newline character)
    assert "\n" not in result


def test_repr_escapes_carriage_return_in_text() -> None:
    """repr(Todo) with \\r in text should be escaped, not overwrite output."""
    todo = Todo(id=1, text="Valid task\r[ ] FAKE")
    result = repr(todo)
    # Should contain escaped representation
    assert "\\r" in result
    # Should not contain actual carriage return
    assert "\r" not in result


def test_repr_escapes_tab_in_text() -> None:
    """repr(Todo) with \\t in text should be escaped visibly."""
    todo = Todo(id=1, text="Task\twith\ttabs")
    result = repr(todo)
    # Should contain escaped representation
    assert "\\t" in result
    # Should not contain actual tab character
    assert "\t" not in result


def test_repr_escapes_ansi_codes_in_text() -> None:
    """ANSI escape sequences in repr should be escaped to prevent terminal injection."""
    todo = Todo(id=1, text="\x1b[31mRed Text\x1b[0m Normal")
    result = repr(todo)
    # Should contain escaped representation
    assert "\\x1b" in result
    # Should not contain actual ESC character
    assert "\x1b" not in result


def test_repr_escapes_null_byte() -> None:
    """Null byte in repr should be escaped."""
    todo = Todo(id=1, text="Before\x00After")
    result = repr(todo)
    assert "\\x00" in result
    assert "\x00" not in result


def test_repr_escapes_backslash() -> None:
    """Backslash should be escaped to prevent ambiguity with escape sequences."""
    todo = Todo(id=1, text="Path\\to\\file")
    result = repr(todo)
    # Backslash should be escaped as \\\\ in the sanitized text
    # Note: Python's !r will also add quotes around the string
    assert "\\\\" in result


def test_repr_normal_text_unchanged() -> None:
    """Normal todo text without control characters should be unchanged."""
    todo = Todo(id=1, text="Buy groceries")
    result = repr(todo)
    # Should contain the text and be single-line
    assert "Buy groceries" in result
    assert "\n" not in result


def test_repr_sanitization_with_truncation() -> None:
    """Long text with control chars should be sanitized before truncation."""
    # Text with newline that will be truncated
    long_text = "A" * 40 + "\nFAKE" + "B" * 60
    todo = Todo(id=1, text=long_text)
    result = repr(todo)

    # Should be single-line (no actual newline)
    assert "\n" not in result
    # Should contain escaped newline
    assert "\\n" in result
    # Should be truncated
    assert "..." in result


def test_repr_with_multiple_control_chars() -> None:
    """Multiple control characters should all be escaped in repr."""
    todo = Todo(id=1, text="Line1\nLine2\rTab\tHere\x00Null")
    result = repr(todo)
    assert "\\n" in result
    assert "\\r" in result
    assert "\\t" in result
    assert "\\x00" in result
    # Should not contain actual control characters
    assert "\n" not in result
    assert "\r" not in result
    assert "\t" not in result
    assert "\x00" not in result


def test_repr_unicode_passes_through() -> None:
    """Unicode characters should pass through unchanged in repr."""
    todo = Todo(id=1, text="Buy café and 日本語")
    result = repr(todo)
    assert "café" in result
    assert "日本語" in result
