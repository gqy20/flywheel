"""Regression tests for Issue #2418: Text width/terminal width support for wrapping long todo text.

This test file ensures that long todo text wraps properly when terminal width is limited,
while preserving the [status] id prefix indentation on wrapped lines.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_short_text_no_wrapping_default_width() -> None:
    """Short todo text should not wrap with default width (80)."""
    todo = Todo(id=1, text="Buy groceries")
    result = TodoFormatter.format_todo(todo)
    # Default width 80 should not wrap short text
    assert result == "[ ]   1 Buy groceries"
    # Should be single line
    assert "\n" not in result


def test_format_todo_short_text_no_wrapping_custom_width() -> None:
    """Short todo text should not wrap with custom width when text fits."""
    todo = Todo(id=1, text="Buy groceries")
    result = TodoFormatter.format_todo(todo, width=40)
    assert result == "[ ]   1 Buy groceries"
    assert "\n" not in result


def test_format_todo_long_text_wraps_with_width() -> None:
    """Long todo text should wrap when width is limited."""
    # Text longer than 40 chars should wrap
    long_text = "This is a very long todo item that needs to be wrapped properly"
    todo = Todo(id=1, text=long_text)

    result = TodoFormatter.format_todo(todo, width=40)

    # Should contain newlines for wrapping
    assert "\n" in result

    # First line should have prefix
    lines = result.split("\n")
    assert lines[0].startswith("[ ]   1 ")

    # Wrapped lines should be indented to align with text (after prefix)
    # The prefix "[ ]   1 " is 8 characters
    for line in lines[1:]:
        assert line.startswith(" " * 8), f"Wrapped line not indented: {line!r}"


def test_format_todo_long_text_no_width_param_backward_compat() -> None:
    """When width parameter is not provided, default to 80 for backward compatibility."""
    long_text = "A" * 100  # 100 'A' characters - longer than 80
    todo = Todo(id=1, text=long_text)

    result = TodoFormatter.format_todo(todo)

    # Should wrap with default width 80
    assert "\n" in result


def test_format_todo_with_status_done_wraps_correctly() -> None:
    """Completed todo with [x] status should wrap correctly."""
    todo = Todo(id=5, text="This is a long todo that is marked as done and needs wrapping", done=True)

    result = TodoFormatter.format_todo(todo, width=40)

    lines = result.split("\n")
    # First line should show [x] for done
    # Format is [x] + space + right-aligned id (3 chars) + space
    # For id=5: [x]   5  (the 5 is right-aligned in 3 chars: '  5')
    assert lines[0].startswith("[x]   5 ")
    # Wrapped lines should be indented
    for line in lines[1:]:
        assert line.startswith(" " * 8), f"Wrapped line not indented: {line!r}"


def test_format_list_with_width_parameter() -> None:
    """format_list should accept width parameter and apply it to all todos."""
    todos = [
        Todo(id=1, text="Short"),
        Todo(id=2, text="This is a much longer todo that will definitely need to be wrapped"),
    ]

    result = TodoFormatter.format_list(todos, width=40)

    lines = result.split("\n")
    # First todo should be single line
    assert "[ ]   1 Short" in lines[0]
    # Second todo should wrap
    assert lines[1].startswith("[ ]   2 This is")
    # Third line should be wrapped continuation
    assert lines[2].startswith(" " * 8)


def test_format_list_empty_with_width() -> None:
    """Empty list should return standard message regardless of width."""
    result = TodoFormatter.format_list([], width=40)
    assert result == "No todos yet."


def test_format_todo_preserves_sanitized_control_chars_when_wrapping() -> None:
    """Wrapped text should still have control characters sanitized."""
    # Text with control char that needs wrapping
    long_text_with_newline = "Start " + "A" * 50 + "\nEnd"
    todo = Todo(id=1, text=long_text_with_newline)

    result = TodoFormatter.format_todo(todo, width=40)

    # Should wrap due to length
    assert "\n" in result
    # Should have escaped newline, not actual newline
    assert "\\n" in result
    # Should not have actual newline character in sanitized output
    # (the \n in result is from wrapping, not from the text)
    lines = result.split("\n")
    # The escaped \n should appear in one of the lines
    assert any("\\n" in line for line in lines)


def test_format_todo_two_digit_id_wrapping_indentation() -> None:
    """Wrapped lines should indent correctly regardless of id digit count."""
    todo = Todo(id=42, text="This is a long todo with two digit id that needs proper wrapping")

    result = TodoFormatter.format_todo(todo, width=40)

    lines = result.split("\n")
    # First line format: "[ ]  42 " (note spacing for 2-digit id)
    assert lines[0].startswith("[ ]  42 ")
    # Wrapped lines should align with text start
    # For id 42, prefix is "[ ]  42 " which is 8 chars
    for line in lines[1:]:
        assert line.startswith(" " * 8), f"Wrapped line not indented correctly: {line!r}"


def test_format_todo_three_digit_id_wrapping_indentation() -> None:
    """Wrapped lines should indent correctly for three-digit ids."""
    todo = Todo(id=100, text="This is a very long todo item with a three digit id number")

    result = TodoFormatter.format_todo(todo, width=40)

    lines = result.split("\n")
    # First line format: "[ ] 100 " (note spacing for 3-digit id)
    assert lines[0].startswith("[ ] 100 ")
    # For id 100, prefix is still 8 chars total
    for line in lines[1:]:
        assert line.startswith(" " * 8), f"Wrapped line not indented correctly: {line!r}"


def test_format_todo_exact_width_boundary() -> None:
    """Text exactly at width boundary should fit on one line."""
    # Create text that will exactly fill the first line
    # Prefix "[ ]   1 " = 8 chars, so we need 32 chars for width=40
    exact_text = "A" * 32
    todo = Todo(id=1, text=exact_text)

    result = TodoFormatter.format_todo(todo, width=40)

    # Should fit on one line (not wrap)
    lines = result.split("\n")
    assert len(lines) == 1
    assert lines[0] == "[ ]   1 " + "A" * 32

def test_format_todo_one_char_over_boundary_wraps() -> None:
    """Text one character over available width should wrap to second line."""
    # Prefix "[ ]   1 " = 8 chars, so 33 chars with width=40 should wrap
    over_text = "A" * 33
    todo = Todo(id=1, text=over_text)

    result = TodoFormatter.format_todo(todo, width=40)

    # Should wrap to second line
    lines = result.split("\n")
    assert len(lines) == 2
    assert lines[0] == "[ ]   1 " + "A" * 32
    assert lines[1] == " " * 8 + "A"
