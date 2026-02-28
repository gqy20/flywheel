"""Regression tests for Issue #6394: __repr__ control character sanitization.

This test file ensures that control characters in todo.text are properly escaped
in the __repr__ output to prevent terminal output manipulation.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_escapes_newline_in_text() -> None:
    """Todo with \\n in text should have escaped newline in repr, not actual newline."""
    todo = Todo(id=1, text="Buy milk\n[ ] FAKE_TODO")
    result = repr(todo)
    # Should contain escaped representation, not actual newline
    assert "\\n" in result
    # Should not contain actual newline character
    assert "\n" not in result


def test_repr_escapes_carriage_return_in_text() -> None:
    """Todo with \\r in text should have escaped CR in repr."""
    todo = Todo(id=1, text="Valid task\r[ ] FAKE")
    result = repr(todo)
    # Should contain escaped representation
    assert "\\r" in result
    # Should not contain actual carriage return
    assert "\r" not in result


def test_repr_escapes_tab_in_text() -> None:
    """Todo with \\t in text should have escaped tab in repr."""
    todo = Todo(id=1, text="Task\twith\ttabs")
    result = repr(todo)
    # Should contain escaped representation
    assert "\\t" in result
    # Should not contain actual tab character
    assert "\t" not in result


def test_repr_escapes_ansi_codes_in_text() -> None:
    """ANSI escape sequences should be escaped in repr to prevent terminal injection."""
    todo = Todo(id=1, text="\x1b[31mRed Text\x1b[0m Normal")
    result = repr(todo)
    # Should contain escaped representation
    assert "\\x1b" in result
    # Should not contain actual ESC character
    assert "\x1b" not in result


def test_repr_escapes_null_byte() -> None:
    """Null byte should be escaped in repr."""
    todo = Todo(id=1, text="Before\x00After")
    result = repr(todo)
    assert "\\x00" in result
    assert "\x00" not in result


def test_repr_normal_text_unchanged() -> None:
    """Normal todo text without control characters should be unchanged."""
    todo = Todo(id=1, text="Buy groceries")
    result = repr(todo)
    assert "Buy groceries" in result
    assert result == "Todo(id=1, text='Buy groceries', done=False)"


def test_repr_with_unicode() -> None:
    """Unicode characters should pass through unchanged."""
    todo = Todo(id=1, text="Buy café and 日本語")
    result = repr(todo)
    assert "café" in result
    assert "日本語" in result


def test_repr_truncates_long_text_with_sanitization() -> None:
    """Long text should be sanitized, with control chars escaped even when truncated."""
    # Create text where control char appears within first 47 chars
    # so it appears in the truncated output
    todo = Todo(id=1, text="A" * 40 + "\n" + "B" * 20)
    result = repr(todo)
    # Should be truncated (with ...)
    assert "..." in result
    # The escaped newline (\\n = 2 chars) should be in the output
    # since the newline is within the first 47 characters
    assert "\\n" in result
    # No actual newline character should be present
    assert "\n" not in result
