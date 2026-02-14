"""Regression tests for Issue #3157: Unicode line/paragraph separator sanitization.

This test file ensures that Unicode line separator (U+2028) and paragraph
separator (U+2029) are properly escaped to prevent fake todo injection.
These characters cause visual line breaks similar to \\n and can be used
to inject fake todo items.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


def test_sanitize_text_escapes_unicode_line_separator() -> None:
    """Unicode line separator U+2028 should be escaped, not rendered as line break."""
    text = "A\u2028B"
    result = _sanitize_text(text)
    # Should contain escaped representation
    assert "\\u2028" in result
    # Should not contain actual U+2028 character
    assert "\u2028" not in result


def test_sanitize_text_escapes_unicode_paragraph_separator() -> None:
    """Unicode paragraph separator U+2029 should be escaped, not rendered as line break."""
    text = "A\u2029B"
    result = _sanitize_text(text)
    # Should contain escaped representation
    assert "\\u2029" in result
    # Should not contain actual U+2029 character
    assert "\u2029" not in result


def test_format_todo_no_fake_injection_via_unicode_line_sep() -> None:
    """Todo with U+2028 should not allow fake todo injection via visual line break."""
    todo = Todo(id=1, text="Buy milk\u2028[ ] FAKE_TODO")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation, not actual line separator
    assert "\\u2028" in result
    # Should not contain actual U+2028 character
    assert "\u2028" not in result
    # Should show both parts on same line (no actual line break)
    assert result == "[ ]   1 Buy milk\\u2028[ ] FAKE_TODO"


def test_format_todo_no_fake_injection_via_unicode_paragraph_sep() -> None:
    """Todo with U+2029 should not allow fake todo injection via visual paragraph break."""
    todo = Todo(id=1, text="Buy milk\u2029[ ] FAKE_TODO")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation, not actual paragraph separator
    assert "\\u2029" in result
    # Should not contain actual U+2029 character
    assert "\u2029" not in result
    # Should show both parts on same line (no actual line break)
    assert result == "[ ]   1 Buy milk\\u2029[ ] FAKE_TODO"


def test_format_todo_with_mixed_unicode_line_breaks() -> None:
    """Todo with both U+2028 and U+2029 should escape both."""
    todo = Todo(id=1, text="Line1\u2028Line2\u2029Line3")
    result = TodoFormatter.format_todo(todo)
    assert "\\u2028" in result
    assert "\\u2029" in result
    # Should not contain actual separator characters
    assert "\u2028" not in result
    assert "\u2029" not in result
