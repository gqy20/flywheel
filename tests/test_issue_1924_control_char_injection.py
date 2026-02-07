"""Regression tests for issue #1924: Control character injection in format_todo.

Issue: format_todo does not sanitize todo.text, allowing control character injection
that can manipulate terminal output (newlines, carriage returns, ANSI codes, etc.).

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_sanitizes_newline_character() -> None:
    """Issue #1924: Newline in todo.text should be escaped or removed.

    Before fix: Output contains literal newlines, breaking single-line format
    After fix: Newline should be escaped as \\n or removed
    """
    todo = Todo(id=1, text="Buy milk\n[EVIL] Injected fake todo", done=False)
    result = TodoFormatter.format_todo(todo)

    # Result should be a single line (no embedded newlines)
    assert "\n" not in result, "Newline character should be escaped or removed"
    # The newline should be visible in escaped form, not functional
    assert "\\n" in result, "Newline should be visible as escape sequence"


def test_format_todo_sanitizes_carriage_return() -> None:
    """Issue #1924: Carriage return in todo.text should be escaped."""
    todo = Todo(id=2, text="Normal text\rOverwrite prefix", done=False)
    result = TodoFormatter.format_todo(todo)

    # Carriage return should not be present in output
    assert "\r" not in result, "Carriage return should be escaped or removed"


def test_format_todo_sanitizes_tab_character() -> None:
    """Issue #1924: Tab in todo.text should be escaped or replaced."""
    todo = Todo(id=3, text="Task\twith\ttabs", done=False)
    result = TodoFormatter.format_todo(todo)

    # Tab should be escaped or replaced (preferably with visible representation)
    # Either tab is gone or represented as \t or spaces
    assert "\t" not in result or result.count("\\t") > 0, "Tab should be escaped or removed"


def test_format_todo_sanitizes_ansi_escape_codes() -> None:
    """Issue #1924: ANSI escape codes should be neutralized.

    Before fix: ANSI codes can change terminal colors, hide text, etc.
    After fix: Escape sequences should be visible as text, not interpreted
    """
    todo = Todo(
        id=4,
        text="\x1b[31mRED TEXT\x1b[0m Normal text",
        done=False
    )
    result = TodoFormatter.format_todo(todo)

    # ANSI escape character should not be present as raw byte
    assert "\x1b" not in result, "ANSI escape character should be escaped"
    # The ESC sequence representation should be visible, not functional
    assert "\\x1b" in result or "\\033" in result or "[31m" not in result


def test_format_todo_sanitizes_multiple_control_chars() -> None:
    """Issue #1924: Multiple control characters should all be sanitized."""
    todo = Todo(
        id=5,
        text="Text\nwith\rmany\t\x1b[31mcontrol\x1b[0mchars",
        done=False
    )
    result = TodoFormatter.format_todo(todo)

    # None of these control characters should be in the raw output
    assert "\n" not in result, "Newline should be escaped"
    assert "\r" not in result, "Carriage return should be escaped"
    assert "\t" not in result, "Tab should be escaped"
    assert "\x1b" not in result, "ANSI escape should be escaped"

    # Should be a single line output
    lines = result.split("\n")
    assert len(lines) == 1, f"Output should be single line, got {len(lines)}"


def test_format_list_sanitizes_all_todos() -> None:
    """Issue #1924: format_list should also sanitize control characters."""
    todos = [
        Todo(id=1, text="Normal todo", done=False),
        Todo(id=2, text="Todo\nwith\nnewlines", done=False),
        Todo(id=3, text="Todo\rwith\rcarriage", done=True),
    ]
    result = TodoFormatter.format_list(todos)

    # Check that newlines are properly escaped
    # Only expected newlines are between todos (format_list uses "\n".join())
    # Newlines within individual todo text should be escaped
    todo_lines = result.split("\n")
    assert len(todo_lines) == 3, f"Should have exactly 3 lines, got {len(todo_lines)}"

    # First line should be normal
    assert "Normal todo" in todo_lines[0]
    # Second line should not contain literal newline within the todo text portion
    # (the text "Todo\nwith\nnewlines" should be escaped)
    assert "\\n" in todo_lines[1] or "Todo" in todo_lines[1]
    # Third line similar check
    assert "\\r" in todo_lines[2] or "Todo" in todo_lines[2]


def test_format_todo_preserves_normal_text() -> None:
    """Issue #1924: Normal text without control characters should be unchanged."""
    todo = Todo(id=1, text="Buy groceries and walk the dog", done=False)
    result = TodoFormatter.format_todo(todo)

    assert result == "[ ]   1 Buy groceries and walk the dog"


def test_format_todo_preserves_special_printable_chars() -> None:
    """Issue #1924: Printable special characters should be preserved."""
    todo = Todo(id=1, text="Price: $50.00 | Discount: 20% | Status: OK!", done=False)
    result = TodoFormatter.format_todo(todo)

    assert "$50.00" in result
    assert "20%" in result
    assert "OK!" in result
    assert "|" in result
