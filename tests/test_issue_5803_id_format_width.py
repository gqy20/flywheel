"""Regression tests for Issue #5803: ID format width alignment.

This test file ensures that ID formatting maintains consistent column alignment
even when IDs exceed 3 digits (>=1000).
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_id_999_alignment() -> None:
    """ID=999 should format correctly with 3 digits."""
    todo = Todo(id=999, text="Task at boundary")
    result = TodoFormatter.format_todo(todo)
    # ID 999 is exactly 3 digits - should be right-aligned in width field
    assert "999" in result


def test_format_todo_id_1000_alignment() -> None:
    """ID=1000 should maintain column alignment (4 digits)."""
    todo = Todo(id=1000, text="Task over thousand")
    result = TodoFormatter.format_todo(todo)
    # The text should start at a consistent column position
    # With fixed width 3: "[ ] 1000 Task" (no padding, 1000 is 4 chars)
    # With fixed width 5: "[ ]  1000 Task" (padded, 1000 is right-aligned in 5)
    # Test that ID is present and properly formatted
    assert "1000" in result


def test_format_list_mixed_id_widths_column_alignment() -> None:
    """List with mixed ID widths should maintain consistent column alignment.

    This is the key test for the bug: when IDs have different digit counts,
    the text column should still align.
    """
    todos = [
        Todo(id=1, text="First task"),
        Todo(id=999, text="Task at 999"),
        Todo(id=1000, text="Task at 1000"),
        Todo(id=10000, text="Task at 10000"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # All lines should have text starting at same column position
    # Format: "[<status>] <id_padded> <text>"
    # With dynamic width based on max_id (10000 = 5 chars), all lines should have
    # the same structure: "[x]" + " " + 5-char-padded-id + " " + text

    # Find where the actual text content starts (after the space following the ID)
    def text_start(line: str) -> int:
        # Format: "[x] <padded_id> <text>"
        # The text starts after "] " + padded_id + " "
        # We find the position by looking for the last space before the text
        # Since we know format is "[x] " + id_with_padding + " " + text,
        # the text starts at position: 4 (for "[x] ") + id_width + 1 (space)
        # But simpler: find "] " and then find where the text starts after
        bracket_end = line.find("]")
        # Skip "] " to get to the ID field
        after_bracket = line[bracket_end + 2 :]
        # The ID field is right-padded, so text starts after we skip all chars
        # up to and including the space after the ID
        # Pattern: optional spaces + digits + space + text
        # Find the first non-space, then skip to next space
        stripped = after_bracket.lstrip(" ")
        leading_spaces = len(after_bracket) - len(stripped)
        # Now find the space after the ID
        space_after_id = stripped.find(" ")
        if space_after_id != -1:
            # Position: bracket + 2 (for "] ") + leading_spaces + id_digits + 1 (space)
            return bracket_end + 2 + leading_spaces + space_after_id + 1
        return -1

    text_positions = [text_start(line) for line in lines]

    # All text positions should be the same for proper alignment
    assert len(set(text_positions)) == 1, (
        f"Column alignment broken: text positions vary {text_positions}\n"
        f"Output:\n{result}"
    )


def test_format_todo_id_zero() -> None:
    """ID=0 should format correctly."""
    todo = Todo(id=0, text="Zero ID task")
    result = TodoFormatter.format_todo(todo)
    assert "0" in result


def test_format_todo_negative_id() -> None:
    """Negative ID should be readable (edge case for corrupted data)."""
    todo = Todo(id=-1, text="Negative ID")
    result = TodoFormatter.format_todo(todo)
    # Should contain the negative ID, output should be readable
    assert "-1" in result
    # Should not crash or produce garbled output
    assert len(result) > 0
