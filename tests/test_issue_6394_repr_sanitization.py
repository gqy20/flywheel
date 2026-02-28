"""Regression tests for Issue #6394: __repr__ control character sanitization.

This test file ensures that control characters in todo.text are properly escaped
in the __repr__ output to prevent terminal output manipulation.
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_escapes_newline_in_text() -> None:
    """Todo.__repr__ with \\n in text should output escaped newline, not actual newline."""
    todo = Todo(id=1, text="Buy milk\nFAKE")
    result = repr(todo)
    # Should contain escaped representation, not actual newline
    assert "\\n" in result
    # Should not contain actual newline character
    assert "\n" not in result


def test_repr_escapes_carriage_return_in_text() -> None:
    """Todo.__repr__ with \\r in text should be escaped, not overwrite output."""
    todo = Todo(id=1, text="Valid task\rFAKE")
    result = repr(todo)
    # Should contain escaped representation
    assert "\\r" in result
    # Should not contain actual carriage return
    assert "\r" not in result


def test_repr_escapes_tab_in_text() -> None:
    """Todo.__repr__ with \\t in text should be escaped visibly."""
    todo = Todo(id=1, text="Task\twith\ttabs")
    result = repr(todo)
    # Should contain escaped representation
    assert "\\t" in result
    # Should not contain actual tab character
    assert "\t" not in result


def test_repr_escapes_multiple_control_chars() -> None:
    """Todo.__repr__ with mixed control characters should all be escaped."""
    todo = Todo(id=1, text="Line1\nLine2\rTab\tHere")
    result = repr(todo)
    assert "\\n" in result
    assert "\\r" in result
    assert "\\t" in result
    # Should not contain actual control characters
    assert "\n" not in result
    assert "\r" not in result
    assert "\t" not in result


def test_repr_escapes_ansi_codes_in_text() -> None:
    """ANSI escape sequences should be escaped in __repr__ to prevent terminal injection."""
    todo = Todo(id=1, text="\x1b[31mRed Text\x1b[0m Normal")
    result = repr(todo)
    # Should contain escaped representation
    assert "\\x1b" in result
    # Should not contain actual ESC character
    assert "\x1b" not in result


def test_repr_escapes_null_byte() -> None:
    """Null byte should be escaped in __repr__."""
    todo = Todo(id=1, text="Before\x00After")
    result = repr(todo)
    assert "\\x00" in result
    assert "\x00" not in result


def test_repr_normal_text_unchanged() -> None:
    """Normal todo text without control characters should be unchanged."""
    todo = Todo(id=1, text="Buy groceries")
    result = repr(todo)
    assert "Buy groceries" in result
    assert "Todo" in result
    assert "id=1" in result
    assert "done=False" in result


def test_repr_with_unicode() -> None:
    """Unicode characters should pass through unchanged in __repr__."""
    todo = Todo(id=1, text="Buy café and 日本語")
    result = repr(todo)
    assert "café" in result
    assert "日本語" in result
