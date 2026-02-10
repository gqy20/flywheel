"""Regression tests for Issue #1948: Control character sanitization in todo.text.

This test file verifies that control characters in todo.text are properly sanitized
to prevent terminal injection attacks via ANSI escape sequences or newline/carriage
return attacks.

Security Issue: https://github.com/gqy20/flywheel/issues/1948
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


def test_format_todo_sanitizes_newline_prevents_fake_task_injection() -> None:
    """Newline in todo.text should be escaped to prevent fake task injection.

    Attack scenario: User creates todo with text like "Buy milk\n[ ] FAKE_TODO"
    to inject a fake unchecked todo item in the list output.
    """
    todo = Todo(id=1, text="Buy milk\n[ ] FAKE_TODO")
    result = TodoFormatter.format_todo(todo)
    # Should be a single line (no actual newline)
    assert "\n" not in result
    # Should show escaped representation
    assert "\\n" in result
    # Full output should be single line with escaped content
    assert result == "[ ]   1 Buy milk\\n[ ] FAKE_TODO"


def test_format_todo_sanitizes_carriage_return_prevents_overwrite() -> None:
    """Carriage return in todo.text should be escaped to prevent output overwrite.

    Attack scenario: User creates todo with text containing \r to overwrite
    previous output on the terminal line.
    """
    todo = Todo(id=1, text="Valid task\r[ ] FAKE")
    result = TodoFormatter.format_todo(todo)
    # Should not contain actual carriage return
    assert "\r" not in result
    # Should show escaped representation
    assert "\\r" in result


def test_format_todo_sanitizes_ansi_escape_sequences_prevents_terminal_injection() -> None:
    """ANSI escape sequences should be escaped to prevent terminal manipulation.

    Attack scenario: User creates todo with ANSI codes like \x1b[31m to change
    terminal colors or execute other terminal commands.
    """
    todo = Todo(id=1, text="\x1b[31mRed Text\x1b[0m Normal")
    result = TodoFormatter.format_todo(todo)
    # Should not contain actual ESC character (0x1b)
    assert "\x1b" not in result
    # Should show escaped hex representation
    assert "\\x1b" in result


def test_format_todo_sanitizes_null_byte() -> None:
    """Null byte should be escaped to prevent string truncation issues.

    Null bytes can cause issues with terminal display and string handling.
    """
    todo = Todo(id=1, text="Before\x00After")
    result = TodoFormatter.format_todo(todo)
    # Should not contain actual null byte
    assert "\x00" not in result
    # Should show escaped representation
    assert "\\x00" in result


def test_format_todo_sanitizes_tab_character() -> None:
    """Tab character should be escaped for consistent display.

    Tabs can cause alignment issues in terminal output.
    """
    todo = Todo(id=1, text="Task\twith\ttabs")
    result = TodoFormatter.format_todo(todo)
    # Should not contain actual tab character
    assert "\t" not in result
    # Should show escaped representation
    assert "\\t" in result


def test_format_todo_normal_text_unchanged() -> None:
    """Normal todo text without control characters should be unchanged.

    Acceptance criteria: Safe todos should display normally without alteration.
    """
    todo = Todo(id=1, text="Buy groceries")
    result = TodoFormatter.format_todo(todo)
    assert result == "[ ]   1 Buy groceries"


def test_format_todo_with_unicode_unchanged() -> None:
    """Unicode characters should pass through unchanged.

    Acceptance criteria: Valid Unicode should not be affected by sanitization.
    """
    todo = Todo(id=1, text="Buy café and 日本語")
    result = TodoFormatter.format_todo(todo)
    assert "café" in result
    assert "日本語" in result


def test_format_list_with_control_chars_each_sanitized() -> None:
    """Multiple todos with control chars should each be sanitized in list output.

    This verifies the fix applies to the list view as well as individual todos.
    """
    todos = [
        Todo(id=1, text="Task 1\nFake task"),
        Todo(id=2, text="Task 2\tTabbed"),
        Todo(id=3, text="Normal task"),
    ]
    result = TodoFormatter.format_list(todos)
    # Each todo should be on its own line (3 lines total)
    lines = result.split("\n")
    assert len(lines) == 3
    # The fake tasks should be escaped
    assert "\\n" in lines[0]
    assert "\\t" in lines[1]
    # Normal task should be unchanged
    assert "Normal task" in lines[2]


def test_sanitize_text_full_control_char_range() -> None:
    """Verify all C0 control characters (0x00-0x1f) are escaped.

    This is a comprehensive check for the full range of ASCII control characters.
    """
    from flywheel.formatter import _sanitize_text

    # Test a selection of C0 control characters
    assert "\\x00" in _sanitize_text("test\x00end")
    assert "\\x01" in _sanitize_text("test\x01end")
    assert "\\x02" in _sanitize_text("test\x02end")
    assert "\\x07" in _sanitize_text("test\x07end")  # BEL
    assert "\\x08" in _sanitize_text("test\x08end")  # Backspace
    assert "\\x1b" in _sanitize_text("test\x1bend")  # ESC
    assert "\\x1f" in _sanitize_text("test\x1fend")


def test_sanitize_text_del_char_escaped() -> None:
    """DEL character (0x7f) should be escaped."""
    from flywheel.formatter import _sanitize_text

    result = _sanitize_text("test\x7fend")
    assert "\\x7f" in result


def test_sanitize_text_c1_control_chars_escaped() -> None:
    """C1 control characters (0x80-0x9f) should be escaped.

    C1 controls can be interpreted by some UTF-8 terminals for various commands.
    """
    from flywheel.formatter import _sanitize_text

    assert "\\x80" in _sanitize_text("test\x80end")
    assert "\\x9b" in _sanitize_text("test\x9bend")  # CSI
    assert "\\x9f" in _sanitize_text("test\x9fend")  # APC


def test_acceptance_criteria_complete_sanitization() -> None:
    """Verify all acceptance criteria from issue #1948 are met.

    From the issue:
    - Formatter escapes or removes newline (\\n), carriage return (\\r), tab (\\t),
      null byte (\\x00), and ANSI escape sequences (\\x1b) from output
    - When a todo contains control characters, the formatted output renders safely
      without breaking terminal display
    """
    from flywheel.formatter import _sanitize_text

    # Test each character class from acceptance criteria
    todo_with_newline = Todo(id=1, text="test\nmore")
    result_newline = TodoFormatter.format_todo(todo_with_newline)
    assert "\n" not in result_newline and "\\n" in result_newline

    todo_with_cr = Todo(id=2, text="test\rmore")
    result_cr = TodoFormatter.format_todo(todo_with_cr)
    assert "\r" not in result_cr and "\\r" in result_cr

    todo_with_tab = Todo(id=3, text="test\tmore")
    result_tab = TodoFormatter.format_todo(todo_with_tab)
    assert "\t" not in result_tab and "\\t" in result_tab

    todo_with_null = Todo(id=4, text="test\x00more")
    result_null = TodoFormatter.format_todo(todo_with_null)
    assert "\x00" not in result_null and "\\x00" in result_null

    todo_with_ansi = Todo(id=5, text="test\x1b[31mred")
    result_ansi = TodoFormatter.format_todo(todo_with_ansi)
    assert "\x1b" not in result_ansi and "\\x1b" in result_ansi

    # Verify normal text still works
    normal_result = _sanitize_text("normal text")
    assert normal_result == "normal text"
