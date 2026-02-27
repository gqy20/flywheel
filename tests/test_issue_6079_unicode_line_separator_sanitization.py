"""Regression tests for Issue #6079: Unicode line/paragraph separator sanitization.

This test file ensures that Unicode line separator (U+2028) and paragraph separator (U+2029)
are properly escaped to prevent log injection or format disruption.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


def test_sanitize_text_escapes_unicode_line_separator() -> None:
    """U+2028 (LINE SEPARATOR) should be escaped to \\u2028."""
    input_text = "a\u2028b"
    result = _sanitize_text(input_text)
    # Should contain escaped representation, not actual U+2028
    assert "\\u2028" in result
    assert "\u2028" not in result


def test_sanitize_text_escapes_unicode_paragraph_separator() -> None:
    """U+2029 (PARAGRAPH SEPARATOR) should be escaped to \\u2029."""
    input_text = "a\u2029b"
    result = _sanitize_text(input_text)
    # Should contain escaped representation, not actual U+2029
    assert "\\u2029" in result
    assert "\u2029" not in result


def test_format_todo_escapes_unicode_line_separator() -> None:
    """Todo with U+2028 in text should output escaped representation."""
    todo = Todo(id=1, text="Buy milk\u2028[ ] FAKE_TODO")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\u2028" in result
    # Should not contain actual U+2028 character
    assert "\u2028" not in result


def test_format_todo_escapes_unicode_paragraph_separator() -> None:
    """Todo with U+2029 in text should output escaped representation."""
    todo = Todo(id=1, text="Valid task\u2029[ ] FAKE")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\u2029" in result
    # Should not contain actual U+2029 character
    assert "\u2029" not in result


def test_format_todo_escapes_mixed_unicode_separators() -> None:
    """Todo with both U+2028 and U+2029 should escape both."""
    todo = Todo(id=1, text="Line1\u2028Line2\u2029Para2")
    result = TodoFormatter.format_todo(todo)
    assert "\\u2028" in result
    assert "\\u2029" in result
    # Should not contain actual separator characters
    assert "\u2028" not in result
    assert "\u2029" not in result
