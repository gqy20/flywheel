"""Regression tests for Issue #2418: Text width/terminal width support.

This test file ensures that long todo text is wrapped to fit within specified
terminal width while preserving proper indentation of wrapped lines.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_short_text_no_wrapping() -> None:
    """Short todo text should not be wrapped."""
    todo = Todo(id=1, text="Buy milk")
    result = TodoFormatter.format_todo(todo)
    # Should be single line
    assert "\n" not in result
    # Should show full todo
    assert result == "[ ]   1 Buy milk"


def test_format_todo_long_text_wraps_at_default_width() -> None:
    """Long todo text should wrap at default width (80)."""
    # Create text that's longer than 80 characters including prefix
    long_text = "This is a very long todo item that exceeds the default terminal width of eighty characters and should wrap"
    todo = Todo(id=1, text=long_text)
    result = TodoFormatter.format_todo(todo)
    # Result should contain newlines for wrapping
    assert "\n" in result
    # First line should have the prefix
    lines = result.split("\n")
    assert lines[0].startswith("[ ]   1 ")
    # Wrapped lines should be indented (same width as prefix)
    for line in lines[1:]:
        assert line.startswith("       ")  # 7 spaces for indentation


def test_format_todo_custom_width_40() -> None:
    """Todo text should wrap at custom width of 40."""
    # Text that's longer than 40 characters
    text = "This is a moderately long todo that will wrap at forty characters width"
    todo = Todo(id=1, text=text)
    result = TodoFormatter.format_todo(todo, width=40)
    # Result should contain newlines for wrapping
    assert "\n" in result
    lines = result.split("\n")
    # Each line should not exceed 40 characters
    for line in lines:
        assert len(line) <= 40


def test_format_todo_custom_width_120_no_wrap() -> None:
    """Todo text should not wrap if width is large enough."""
    # Text shorter than 120 characters
    text = "This is a reasonably short todo"
    todo = Todo(id=1, text=text)
    result = TodoFormatter.format_todo(todo, width=120)
    # Should be single line (no wrapping needed)
    assert "\n" not in result
    assert result == "[ ]   1 This is a reasonably short todo"


def test_format_todo_wrapping_preserves_prefix() -> None:
    """Wrapped lines should preserve [status] id prefix indentation."""
    long_text = "Very long todo text that needs to be wrapped across multiple lines while maintaining proper indentation for readability"
    todo = Todo(id=42, text=long_text)
    result = TodoFormatter.format_todo(todo, width=50)
    lines = result.split("\n")
    # First line should have full prefix
    assert lines[0].startswith("[x]  42 ") if todo.done else lines[0].startswith("[ ]  42 ")
    # Continuation lines should have same indentation as prefix
    prefix_len = len("[ ]  42 ")
    for line in lines[1:]:
        # Continuation lines should start with spaces matching prefix length
        assert line.startswith(" " * prefix_len)


def test_format_list_with_width() -> None:
    """format_list should pass width parameter to format_todo."""
    todos = [
        Todo(id=1, text="Short task"),
        Todo(id=2, text="This is a much longer task that will need to be wrapped when formatted with a narrow width setting"),
        Todo(id=3, text="Another short one"),
    ]
    result = TodoFormatter.format_list(todos, width=40)
    lines = result.split("\n")
    # Should have multiple lines due to wrapping
    assert len(lines) > 3
    # First todo should be on single line
    assert "[ ]   1 Short task" in lines[0]
    # Second todo should be wrapped
    assert "[ ]   2 This is a much longer" in lines[1]


def test_format_list_default_width_80() -> None:
    """format_list should use default width of 80 when not specified."""
    todos = [
        Todo(id=1, text="A task with reasonably short text"),
        Todo(id=2, text="Another task that also fits within the default width"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")
    # Should have exactly 2 lines (no wrapping needed)
    assert len(lines) == 2


def test_format_todo_width_edge_case_empty_text() -> None:
    """Empty todo text should handle width parameter gracefully."""
    todo = Todo(id=1, text="")
    result = TodoFormatter.format_todo(todo, width=40)
    # Should have prefix even with empty text
    assert result.startswith("[ ]   1 ")


def test_format_todo_width_with_special_chars() -> None:
    """Text wrapping should work with sanitized special characters."""
    # Text with newlines that get sanitized to \n
    todo = Todo(id=1, text="Buy milk\nand eggs\nand bread from the store")
    result = TodoFormatter.format_todo(todo, width=30)
    # Should contain escaped newlines
    assert "\\n" in result
    # Should be wrapped due to length
    assert "\n" in result


def test_format_list_empty_with_width() -> None:
    """Empty list should return standard message regardless of width."""
    result = TodoFormatter.format_list([], width=40)
    assert result == "No todos yet."
