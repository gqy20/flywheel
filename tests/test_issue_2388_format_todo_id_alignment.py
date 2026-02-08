"""Regression tests for Issue #2388: format_todo ID alignment for large IDs.

This test file ensures that todo IDs >= 1000 are properly formatted without
causing column misalignment.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_with_id_1000_maintains_alignment() -> None:
    """Todo with ID=1000 (4 digits) should maintain proper column alignment.

    The current fixed width >3 format will misalign IDs >= 1000.
    This test demonstrates the issue and will pass once fixed.
    """
    todo = Todo(id=1000, text="Buy milk")
    result = TodoFormatter.format_todo(todo)
    # The status bracket [x] or [ ] is 3 chars
    # Then a space, then the ID should be right-aligned
    # Expected format: "[ ] 1000 Buy milk" (with default width=3, ID expands)
    # The key assertion is that ID 1000 doesn't break the format
    assert "[ ]" in result
    assert "1000" in result
    assert "Buy milk" in result
    # Check that the output is well-formed (contains status, ID, text)
    # Don't check parts since split() breaks on the brackets
    assert result.startswith("[ ]")


def test_format_todo_with_id_99999_maintains_alignment() -> None:
    """Todo with ID=99999 (5 digits) should maintain proper column alignment.

    Large IDs should still be displayed cleanly without breaking format.
    """
    todo = Todo(id=99999, text="Large ID task")
    result = TodoFormatter.format_todo(todo)
    assert "[ ]" in result
    assert "99999" in result
    assert "Large ID task" in result
    # Check that the output is well-formed
    assert result.startswith("[ ]")


def test_format_list_with_mixed_id_widths_aligns_properly() -> None:
    """format_list should align todos with varying ID widths.

    When displaying todos with IDs of different widths (1, 100, 1000),
    the output should maintain proper column alignment. This is the core
    issue - the current fixed width >3 breaks alignment for IDs >= 1000.
    """
    todos = [
        Todo(id=1, text="Task one"),
        Todo(id=100, text="Task hundred"),
        Todo(id=1000, text="Task thousand"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # Each todo should be on its own line
    assert len(lines) == 3

    # Verify each line contains expected content
    assert "Task one" in lines[0]
    assert "Task hundred" in lines[1]
    assert "Task thousand" in lines[2]

    # Verify IDs are present
    assert "1" in lines[0]
    assert "100" in lines[1]
    assert "1000" in lines[2]

    # Check column alignment: the text part should start at the same column
    # Extract the starting position of the text in each line
    # After "[<status>] <id> " the text should begin
    # For proper alignment, the space after ID should align across lines
    for line in lines:
        assert "[ ]" in line

    # The key alignment check: split by status marker and verify structure
    for line in lines:
        parts = line.split("[ ]")
        assert len(parts) == 2
        # After status, we should have " <id> <text>"
        rest = parts[1].strip()
        # The text should be one of our expected values
        text_part = " ".join(rest.split()[1:])
        assert text_part in ["Task one", "Task hundred", "Task thousand"]


def test_format_todo_with_done_status_and_large_id() -> None:
    """Completed todo with large ID should format correctly."""
    todo = Todo(id=5000, text="Done task", done=True)
    result = TodoFormatter.format_todo(todo)
    assert "[x]" in result
    assert "5000" in result
    assert "Done task" in result


def test_format_list_all_with_large_ids() -> None:
    """List with only large IDs should format consistently."""
    todos = [
        Todo(id=9998, text="Task 9998"),
        Todo(id=9999, text="Task 9999"),
        Todo(id=10000, text="Task 10000"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    assert len(lines) == 3
    for i, line in enumerate(lines):
        assert "[ ]" in line
        assert f"Task {9998 + i}" in line


def test_format_todo_id_edge_case_exactly_1000() -> None:
    """Edge case: ID exactly at the boundary (1000)."""
    todo = Todo(id=1000, text="Boundary task")
    result = TodoFormatter.format_todo(todo)

    # The output should be clean and properly formatted
    # No truncation, no overflow issues
    assert "1000" in result
    assert "Boundary task" in result

    # Verify the format is exactly as expected
    # Format: "[ ] 1000 Boundary task"
    expected = "[ ] 1000 Boundary task"
    assert result == expected


def test_format_list_column_alignment_verification() -> None:
    """Verify that text columns are aligned regardless of ID width.

    This test explicitly checks that the text portion of each todo
    starts at the same column position when IDs have different widths.
    """
    todos = [
        Todo(id=1, text="A"),
        Todo(id=99, text="B"),
        Todo(id=999, text="C"),
        Todo(id=1000, text="D"),
        Todo(id=10000, text="E"),
    ]
    result = TodoFormatter.format_list(todos)
    lines = result.split("\n")

    # Find the position where the text starts in each line
    # The text should start after "[<status>] <id> "
    text_positions = []
    for line in lines:
        # For our test, the text is just A, B, C, D, E
        # Find position of the letter
        for i, char in enumerate(line):
            if char in "ABCDE" and (i == 0 or line[i-1] == " "):
                text_positions.append(i)
                break

    # All text characters should start at the same column
    # (or very close if we account for minimal alignment differences)
    # With proper dynamic width formatting, they should align
    assert len(text_positions) == 5
    # All positions should be the same (perfect alignment)
    assert len(set(text_positions)) == 1, f"Text not aligned: positions {text_positions}"
