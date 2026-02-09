"""Regression tests for Issue #2418: text width/terminal width support for wrapping long todo text.

This test file ensures that:
1. format_todo() accepts optional width parameter (default 80)
2. Text longer than width wraps to multiple lines with proper indentation
3. Wrapped lines preserve [status] id prefix indentation
4. format_list() also supports width parameter
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_short_text_no_wrapping() -> None:
    """Short todo text should not wrap even with width specified."""
    todo = Todo(id=1, text="Buy groceries")
    result = TodoFormatter.format_todo(todo, width=80)
    # Should be single line
    assert "\n" not in result
    assert result == "[ ]   1 Buy groceries"


def test_format_todo_long_text_wraps_at_default_width() -> None:
    """Long todo text should wrap at default width of 80."""
    # Create text that's longer than 80 characters total
    long_text = "This is a very long todo item that should wrap when displayed because it exceeds the default terminal width of eighty characters"
    todo = Todo(id=1, text=long_text)
    result = TodoFormatter.format_todo(todo, width=80)
    # Should wrap (contain newline)
    assert "\n" in result
    # First line should start with the prefix
    lines = result.split("\n")
    assert lines[0].startswith("[ ]   1 ")
    # Wrapped lines should be indented to align with the text
    for line in lines[1:]:
        assert line.startswith("       "), f"Wrapped line should have indentation: {line!r}"


def test_format_todo_wraps_at_custom_width() -> None:
    """Long todo text should wrap at custom width."""
    long_text = "This is a long todo that should wrap at forty characters width"
    todo = Todo(id=1, text=long_text)
    result = TodoFormatter.format_todo(todo, width=40)
    # Should wrap (contain newline)
    assert "\n" in result
    # First line should be approximately 40 chars or less
    lines = result.split("\n")
    assert len(lines[0]) <= 40


def test_format_todo_wrapping_preserves_prefix() -> None:
    """Wrapped lines should preserve the [status] id prefix on first line only."""
    long_text = "This is a very long todo item that definitely needs to wrap because it is way too long for a single line of output"
    todo = Todo(id=5, text=long_text)
    result = TodoFormatter.format_todo(todo, width=60)
    lines = result.split("\n")
    # First line has the full prefix
    assert lines[0].startswith("[ ]   5 ")
    # Subsequent lines are indented but don't repeat the prefix
    for line in lines[1:]:
        assert not line.startswith("["), f"Wrapped line should not repeat prefix: {line!r}"


def test_format_todo_done_status_with_wrapping() -> None:
    """Completed todos should show [x] and still wrap correctly."""
    todo = Todo(id=1, text="This is a long todo that is marked as done and should still wrap properly at the specified width", done=True)
    result = TodoFormatter.format_todo(todo, width=60)
    lines = result.split("\n")
    # Should show [x] for done todos
    assert lines[0].startswith("[x]   1 ")
    # Should still wrap
    assert len(lines) > 1


def test_format_list_with_width_parameter() -> None:
    """format_list should pass width parameter to format_todo."""
    todos = [
        Todo(id=1, text="Short"),
        Todo(id=2, text="This is a much longer todo item that will definitely need to wrap when displayed with a narrower width setting"),
        Todo(id=3, text="Another short one"),
    ]
    result = TodoFormatter.format_list(todos, width=50)
    lines = result.split("\n")
    # Second todo should wrap to multiple lines
    # First todo (short) - 1 line
    # Second todo (long) - multiple lines
    # Third todo (short) - 1 line
    assert len(lines) > 3  # More than 3 lines due to wrapping


def test_format_list_default_width() -> None:
    """format_list should use default width of 80 when not specified."""
    todos = [
        Todo(id=1, text="Buy groceries"),
        Todo(id=2, text="Walk the dog"),
    ]
    result = TodoFormatter.format_list(todos)
    # With default width and short text, should be exactly 2 lines
    lines = result.split("\n")
    assert len(lines) == 2
    assert "[ ]   1 Buy groceries" in lines[0]
    assert "[ ]   2 Walk the dog" in lines[1]


def test_format_list_empty_with_width() -> None:
    """Empty list should return standard message even with width specified."""
    result = TodoFormatter.format_list([], width=40)
    assert result == "No todos yet."


def test_format_todo_width_equals_prefix_length() -> None:
    """Even very narrow width should work (edge case)."""
    todo = Todo(id=1, text="X")
    # Width of 7 is just enough for "[ ]   1 " prefix (7 chars)
    result = TodoFormatter.format_todo(todo, width=7)
    # Should at least not crash and produce valid output
    assert "[ ]   1 X" in result or "[ ]   1" in result


def test_format_todo_with_control_chars_and_wrapping() -> None:
    """Control character sanitization should work together with wrapping."""
    # Text with control char that needs wrapping
    long_text = "This is a long todo with a newline\nthat should be escaped and then wrapped properly because it exceeds the width"
    todo = Todo(id=1, text=long_text)
    result = TodoFormatter.format_todo(todo, width=60)
    # Should have escaped newline (sanitization)
    assert "\\n" in result
    # Should also wrap due to length
    assert "\n" in result  # Actual newlines from wrapping
    # Should not have the actual control character
    assert "\r" not in result
