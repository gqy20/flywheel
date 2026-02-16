"""Regression tests for Issue #3594: ID width specifier alignment for large IDs.

This test file ensures that format_todo aligns IDs correctly when id > 999.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_id_alignment_with_999() -> None:
    """Todo with id=999 should be right-aligned in 3-char width."""
    todo = Todo(id=999, text="Task")
    result = TodoFormatter.format_todo(todo)
    # Should have leading space to right-align 999 in 3-char field
    assert result == "[ ] 999 Task"


def test_format_todo_id_alignment_with_1000() -> None:
    """Todo with id=1000 should still align properly (no misalignment)."""
    todo = Todo(id=1000, text="Task")
    result = TodoFormatter.format_todo(todo)
    # Should align with id field - with dynamic width based on max id in list
    # For single todo, uses width of 4 (4 digits in 1000): "[ ] 1000 Task"
    assert result.startswith("[ ]")
    assert "1000 Task" in result
    # The ID field should be right-aligned with consistent spacing
    # For id=1000 with 4-digit width: "[ ] 1000 Task"
    assert result == "[ ] 1000 Task"


def test_format_todo_id_alignment_with_10000() -> None:
    """Todo with id=10000 should still align properly."""
    todo = Todo(id=10000, text="Task")
    result = TodoFormatter.format_todo(todo)
    assert result.startswith("[ ]")
    assert "10000 Task" in result
    # Should be "[ ] 10000 Task" with 5-digit field (dynamic width)
    assert result == "[ ] 10000 Task"


def test_format_list_with_mixed_id_widths() -> None:
    """format_list should align ids consistently across different widths."""
    todos = [
        Todo(id=1, text="One"),
        Todo(id=99, text="Ninety-nine"),
        Todo(id=999, text="Nine-ninety-nine"),
        Todo(id=1000, text="Thousand"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")
    assert len(lines) == 4

    # All lines should have text starting at the same column (dynamic width)
    # The max ID is 1000 (4 chars), so all IDs should be padded to 4 chars
    # Line format: "[ ] " + padded_id + " " + text
    expected_lines = [
        "[ ]    1 One",              # 1 padded to 4 chars
        "[ ]   99 Ninety-nine",      # 99 padded to 4 chars
        "[ ]  999 Nine-ninety-nine",  # 999 padded to 4 chars
        "[ ] 1000 Thousand",         # 1000 already 4 chars
    ]
    assert lines == expected_lines

    # Verify all IDs are right-aligned to width 4
    for line in lines:
        assert line.startswith("[ ] ")
        # After "[ ] ", there should be exactly 4 characters for ID + space before text
        # Format: "[ ] " + 4-char-ID + " " + text
        assert len(line) > 5  # has content after prefix
        id_field = line[4:8]  # The 4-character ID field (with padding)
        assert id_field[-1].isdigit() or id_field[-1] == " "  # Last char is digit or space


def test_format_list_column_alignment_verification() -> None:
    """Verify column alignment by checking consistent spacing pattern."""
    todos = [
        Todo(id=1, text="First"),
        Todo(id=1000, text="Thousand"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # Both lines should have the same prefix length before the text starts
    # This ensures the text column is aligned
    line1 = lines[0]  # "[ ]    1 First" or "[ ] 1 First" depending on implementation
    line2 = lines[1]  # "[ ] 1000 Thousand"

    # Extract the text part (everything after the ID)
    # Both should have text starting at the same position relative to their ID widths
    # or with dynamic width, text should start at the same absolute column

    # With consistent formatting: "[ ] " + id + " " + text
    # For dynamic width based on max id, text should align
    prefix_len_1 = line1.index("First")
    prefix_len_2 = line2.index("Thousand")

    # If using dynamic width, both prefixes should have same length
    assert prefix_len_1 == prefix_len_2, (
        f"Text columns should align: line1 prefix={prefix_len_1}, line2 prefix={prefix_len_2}"
    )
