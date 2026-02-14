"""Regression tests for Issue #3269: ID field width format misalignment.

This test file ensures that ID field width accommodates larger IDs (>999)
without breaking table formatting.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_id_single_digit_right_aligned() -> None:
    """ID with single digit should be right-aligned in 4-char field."""
    todo = Todo(id=1, text="Task")
    result = TodoFormatter.format_todo(todo)
    # ID 1 should be right-aligned with 3 spaces before it
    assert result == "[ ]    1 Task"


def test_format_todo_id_double_digit_right_aligned() -> None:
    """ID with double digits should be right-aligned in 4-char field."""
    todo = Todo(id=99, text="Task")
    result = TodoFormatter.format_todo(todo)
    # ID 99 should be right-aligned with 2 spaces before it
    assert result == "[ ]   99 Task"


def test_format_todo_id_triple_digit_right_aligned() -> None:
    """ID with triple digits should be right-aligned in 4-char field."""
    todo = Todo(id=100, text="Task")
    result = TodoFormatter.format_todo(todo)
    # ID 100 should be right-aligned with 1 space before it
    assert result == "[ ]  100 Task"


def test_format_todo_id_four_digits_aligned() -> None:
    """ID 9999 should format as '[ ] 9999 text' (aligned, no overflow)."""
    todo = Todo(id=9999, text="text")
    result = TodoFormatter.format_todo(todo)
    assert result == "[ ] 9999 text"


def test_format_todo_id_1000_aligned() -> None:
    """ID 1000 should format correctly with 4-char width."""
    todo = Todo(id=1000, text="Task")
    result = TodoFormatter.format_todo(todo)
    assert result == "[ ] 1000 Task"


def test_format_list_column_alignment_mixed_ids() -> None:
    """format_list() output columns remain aligned for mixed ID sizes."""
    todos = [
        Todo(id=1, text="Task A"),
        Todo(id=100, text="Task B"),
        Todo(id=9999, text="Task C"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # Each line should have the same structure
    # [x] NNNN text (where NNNN is right-aligned in 4-char field)
    # Find where the task text starts (should be same position for all)
    import re

    # Extract the prefix before the task text
    prefixes = []
    for line in lines:
        # Match "[x] " followed by 4-char right-aligned number (with leading spaces) and a space
        match = re.match(r"\[[ x]\] (\s*\d+) ", line)
        assert match, f"Line did not match expected format: {line}"
        prefix = line[: match.end()]
        prefixes.append(prefix)

    # All prefixes should have the same length for alignment
    assert len({len(p) for p in prefixes}) == 1, (
        f"Prefixes have different lengths, columns misaligned: {prefixes}"
    )
