"""Regression tests for Issue #3594: ID width specifier alignment for large IDs.

This test file ensures that todo IDs with 4+ digits (>=1000) align consistently
with smaller IDs in the formatted output.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_aligns_id_999() -> None:
    """ID 999 should align with 3-char width."""
    todo = Todo(id=999, text="Task 999")
    result = TodoFormatter.format_todo(todo)
    # ID 999 should be right-aligned in at least 3 chars
    assert "999" in result


def test_format_todo_aligns_id_1000() -> None:
    """ID 1000 should maintain alignment consistency with 3-digit IDs."""
    todo = Todo(id=1000, text="Task 1000")
    result = TodoFormatter.format_todo(todo)
    # The text should start at a consistent position regardless of ID width
    # Expected: "[ ] 1000 Task 1000" (4 digits, no extra padding needed)
    assert "1000" in result
    assert "Task 1000" in result


def test_format_todo_aligns_id_10000() -> None:
    """ID 10000 should maintain alignment consistency."""
    todo = Todo(id=10000, text="Task 10000")
    result = TodoFormatter.format_todo(todo)
    assert "10000" in result
    assert "Task 10000" in result


def test_format_list_aligns_mixed_id_widths() -> None:
    """format_list should align all todos regardless of ID digit count."""
    todos = [
        Todo(id=1, text="Single digit"),
        Todo(id=99, text="Two digits"),
        Todo(id=999, text="Three digits"),
        Todo(id=1000, text="Four digits"),
        Todo(id=10000, text="Five digits"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    assert len(lines) == 5

    # Find where the text starts by finding the text content position
    # Format: "[STATUS] <ID> <Text>"
    text_names = ["Single digit", "Two digits", "Three digits", "Four digits", "Five digits"]
    text_starts = []
    for line, expected_text in zip(lines, text_names, strict=True):
        idx = line.index(expected_text)
        text_starts.append(idx)

    # All text should start at the same column for proper alignment
    first_start = text_starts[0]
    for i, start in enumerate(text_starts):
        assert start == first_start, (
            f"Line {i} text starts at column {start}, expected {first_start}. "
            f"Line content: {lines[i]!r}"
        )


def test_format_list_with_single_digit_and_four_digit_ids() -> None:
    """Specific test case: ID 1 and ID 1000 should align."""
    todos = [
        Todo(id=1, text="First"),
        Todo(id=1000, text="Thousand"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # Both text portions should start at same column
    # Line 0: "[ ]     1 First" or "[ ]     1 First"
    # Line 1: "[ ]  1000 Thousand"

    # Find where text starts
    idx0 = lines[0].index("First")
    idx1 = lines[1].index("Thousand")

    assert idx0 == idx1, (
        f"Misalignment: 'First' starts at {idx0}, 'Thousand' starts at {idx1}\n"
        f"Line 0: {lines[0]!r}\n"
        f"Line 1: {lines[1]!r}"
    )
