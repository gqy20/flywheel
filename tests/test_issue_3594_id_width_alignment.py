"""Regression tests for Issue #3594: ID width specifier alignment.

This test file ensures that todo IDs maintain consistent alignment regardless
of the number of digits in the ID.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_id_alignment_single_digit() -> None:
    """Single digit ID should be right-aligned with padding."""
    todo = Todo(id=1, text="Test task")
    result = TodoFormatter.format_todo(todo)
    assert result == "[ ]   1 Test task"


def test_format_todo_id_alignment_two_digits() -> None:
    """Two digit ID should be right-aligned with padding."""
    todo = Todo(id=99, text="Test task")
    result = TodoFormatter.format_todo(todo)
    assert result == "[ ]  99 Test task"


def test_format_todo_id_alignment_three_digits() -> None:
    """Three digit ID should be right-aligned with minimal padding."""
    todo = Todo(id=999, text="Test task")
    result = TodoFormatter.format_todo(todo)
    assert result == "[ ] 999 Test task"


def test_format_todo_id_alignment_four_digits() -> None:
    """Four digit ID (>= 1000) should maintain alignment with 3-digit IDs."""
    todo = Todo(id=1000, text="Test task")
    result = TodoFormatter.format_todo(todo)
    # The issue: with :>3 specifier, id=1000 outputs "1000" (4 chars) without leading space
    # while id=999 outputs " 999" (with space) - causing misalignment
    # Fix should ensure consistent width across all ID sizes
    assert result == "[ ] 1000 Test task"


def test_format_todo_id_alignment_five_digits() -> None:
    """Five digit ID should also maintain alignment."""
    todo = Todo(id=10000, text="Test task")
    result = TodoFormatter.format_todo(todo)
    assert result == "[ ] 10000 Test task"


def _extract_text_start_position(line: str) -> int:
    """Extract the column position where task text starts.

    Format is "[ ] " + right-padded ID + " " + text
    Returns the column where the actual text begins.
    """
    assert line.startswith("[ ] "), f"Line should start with '[ ] ': {line}"
    rest = line[4:]  # Everything after "[ ] "
    # For right-aligned IDs, the ID field is padded on the LEFT
    # So we need to find where the actual ID ends (last space before text)
    # Actually, we need to find where text starts, which is after the ID + space
    # The pattern is: spaces + ID_digits + space + text
    # We want to find the position of the first non-space after "[ ] "
    # Then find the space after that

    # Strip leading spaces to find where ID number starts
    stripped = rest.lstrip(" ")
    leading_spaces = len(rest) - len(stripped)

    # Find where the ID number ends (next space after ID)
    id_end = stripped.find(" ")
    assert id_end != -1, f"Expected space after ID in: {line}"

    # Text starts at: 4 (for "[ ] ") + leading_spaces + id_end + 1 (for space)
    return 4 + leading_spaces + id_end + 1


def test_format_list_mixed_id_widths_aligned() -> None:
    """List with mixed ID widths should have aligned columns."""
    todos = [
        Todo(id=1, text="Task one"),
        Todo(id=99, text="Task two"),
        Todo(id=999, text="Task three"),
        Todo(id=1000, text="Task four"),
        Todo(id=10000, text="Task five"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # All lines should have the same starting position for the task text
    text_start_positions = [_extract_text_start_position(line) for line in lines]

    first_text_pos = text_start_positions[0]
    for i, pos in enumerate(text_start_positions):
        assert pos == first_text_pos, (
            f"Line {i} text starts at column {pos}, expected {first_text_pos}. "
            f"Lines: {lines}"
        )


def test_format_list_consistent_column_width() -> None:
    """ID column should have consistent width across all rows."""
    todos = [
        Todo(id=1, text="Small"),
        Todo(id=500, text="Medium"),
        Todo(id=9999, text="Large"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # Find the max ID width needed
    max_id_len = max(len(str(t.id)) for t in todos)

    # Verify each line has the ID column padded to consistent width
    # The format should be "[ ] " + right-aligned ID + " " + text
    for i, (line, todo) in enumerate(zip(lines, todos, strict=True)):
        assert line.startswith("[ ] "), f"Line should start with '[ ] ': {line}"
        rest = line[4:]  # Everything after "[ ] "

        # Count leading spaces (padding for right-alignment)
        stripped = rest.lstrip(" ")
        id_len = len(str(todo.id))
        # ID field width = leading_spaces + id_len
        id_field_width = (len(rest) - len(stripped)) + id_len

        assert id_field_width == max_id_len, (
            f"Line {i} ID field width is {id_field_width}, expected {max_id_len}. "
            f"Line: {line}"
        )


def test_format_list_max_id_width_based_on_actual_ids() -> None:
    """ID column width should be based on max ID in the list."""
    # If we only have small IDs, column should be narrow
    small_todos = [Todo(id=1, text="A"), Todo(id=2, text="B")]
    small_result = TodoFormatter.format_list(small_todos)
    small_lines = small_result.split("\n")

    # If we have large IDs, column should be wider
    large_todos = [Todo(id=1, text="A"), Todo(id=10000, text="B")]
    large_result = TodoFormatter.format_list(large_todos)
    large_lines = large_result.split("\n")

    # All text should start at the same position within each list
    small_text_pos = [_extract_text_start_position(line) for line in small_lines]
    assert small_text_pos[0] == small_text_pos[1], (
        f"Text columns misaligned in small list: {small_text_pos}"
    )

    large_text_pos = [_extract_text_start_position(line) for line in large_lines]
    assert large_text_pos[0] == large_text_pos[1], (
        f"Text columns misaligned in large list: {large_text_pos}"
    )

    # Large list should have wider column than small list
    assert large_text_pos[0] > small_text_pos[0], (
        f"Large ID list should have wider column: "
        f"small={small_text_pos[0]}, large={large_text_pos[0]}"
    )
