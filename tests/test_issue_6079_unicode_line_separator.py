"""Regression tests for Issue #6079: Unicode line/paragraph separator sanitization.

Unicode line separator (U+2028) and paragraph separator (U+2029) can create
line breaks in JSON and some text formats, potentially allowing log injection
or format disruption. They should be sanitized.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


def test_sanitize_text_escapes_unicode_line_separator() -> None:
    """U+2028 (LINE SEPARATOR) should be escaped to prevent line breaks."""
    # U+2028 is a Unicode line separator that can cause unexpected line breaks
    text_with_sep = "test\u2028injection"
    result = _sanitize_text(text_with_sep)
    # Should contain escaped representation, not actual U+2028
    assert "\\u2028" in result
    assert "\u2028" not in result


def test_sanitize_text_escapes_unicode_paragraph_separator() -> None:
    """U+2029 (PARAGRAPH SEPARATOR) should be escaped to prevent line breaks."""
    # U+2029 is a Unicode paragraph separator that can cause unexpected line breaks
    text_with_sep = "test\u2029injection"
    result = _sanitize_text(text_with_sep)
    # Should contain escaped representation, not actual U+2029
    assert "\\u2029" in result
    assert "\u2029" not in result


def test_sanitize_text_preserves_other_unicode() -> None:
    """Other Unicode characters should pass through unchanged."""
    # Characters near U+2028/U+2029 should NOT be escaped
    assert _sanitize_text("–") == "–"  # U+2013 (en-dash)
    assert _sanitize_text("—") == "—"  # U+2014 (em-dash)
    assert _sanitize_text("†") == "†"  # U+2020 (dagger)
    assert _sanitize_text("‡") == "‡"  # U+2021 (double dagger)
    # Normal Unicode text
    assert _sanitize_text("日本語") == "日本語"
    assert _sanitize_text("café") == "café"


def test_format_todo_escapes_unicode_line_separator() -> None:
    """Todo with U+2028 should output escaped representation, not actual character."""
    todo = Todo(id=1, text="Buy milk\u2028[ ] FAKE_TODO")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\u2028" in result
    # Should not contain actual U+2028 character
    assert "\u2028" not in result
    # Should be a single line (no actual line break)
    assert result.count("\n") == 0


def test_format_todo_escapes_unicode_paragraph_separator() -> None:
    """Todo with U+2029 should output escaped representation, not actual character."""
    todo = Todo(id=1, text="Buy milk\u2029[ ] FAKE_TODO")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\u2029" in result
    # Should not contain actual U+2029 character
    assert "\u2029" not in result
    # Should be a single line (no actual line break)
    assert result.count("\n") == 0


def test_sanitize_text_both_separators_together() -> None:
    """Both U+2028 and U+2029 should be escaped in the same string."""
    text = "line1\u2028line2\u2029para2"
    result = _sanitize_text(text)
    assert "\\u2028" in result
    assert "\\u2029" in result
    assert "\u2028" not in result
    assert "\u2029" not in result
