"""Regression tests for Issue #7024: Unicode line/paragraph separator sanitization.

This test file ensures that Unicode line separator (U+2028) and paragraph
separator (U+2029) characters are properly escaped to prevent unexpected
line breaks in output.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_escapes_unicode_line_separator() -> None:
    """Todo with U+2028 (Line Separator) should be escaped, not cause line break."""
    # U+2028 is Unicode line separator that can cause unexpected line breaks
    todo = Todo(id=1, text="Task one\u2028Task two")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\u2028" in result
    # Should not contain raw U+2028 character
    assert "\u2028" not in result
    # Should be single line output
    assert "\n" not in result


def test_format_todo_escapes_unicode_paragraph_separator() -> None:
    """Todo with U+2029 (Paragraph Separator) should be escaped, not cause line break."""
    # U+2029 is Unicode paragraph separator that can cause unexpected line breaks
    todo = Todo(id=1, text="Para one\u2029Para two")
    result = TodoFormatter.format_todo(todo)
    # Should contain escaped representation
    assert "\\u2029" in result
    # Should not contain raw U+2029 character
    assert "\u2029" not in result
    # Should be single line output
    assert "\n" not in result


def test_format_todo_escapes_both_unicode_separators() -> None:
    """Todo with both U+2028 and U+2029 should have both escaped."""
    todo = Todo(id=1, text="Line\u2028Para\u2029End")
    result = TodoFormatter.format_todo(todo)
    assert "\\u2028" in result
    assert "\\u2029" in result
    assert "\u2028" not in result
    assert "\u2029" not in result


def test_format_list_with_unicode_separators() -> None:
    """Multiple todos with Unicode separators should all be sanitized."""
    todos = [
        Todo(id=1, text="Task\u2028One"),
        Todo(id=2, text="Task\u2029Two"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")
    # Should be exactly 2 lines (one per todo), not 4
    assert len(lines) == 2
    assert "\\u2028" in lines[0]
    assert "\\u2029" in lines[1]
