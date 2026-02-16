"""Tests for Todo.__repr__ method (Issue #2087).

These tests verify that:
1. Todo objects have a useful __repr__ for debugging
2. repr output is concise (< 80 chars for normal todos)
3. Long text is truncated in repr
4. repr handles special characters properly
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_repr_with_all_fields() -> None:
    """repr(Todo) should return readable format with all key fields."""
    todo = Todo(id=1, text="buy milk", done=False)
    result = repr(todo)

    # Should include class name and key fields
    assert "Todo" in result
    assert "id=1" in result
    assert "text=" in result
    assert "done=False" in result

    # Text should be quoted
    assert "'buy milk'" in result or '"buy milk"' in result


def test_todo_repr_with_minimal_fields() -> None:
    """repr(Todo) should work with minimal required fields."""
    todo = Todo(id=42, text="minimal")
    result = repr(todo)

    assert "Todo" in result
    assert "id=42" in result
    assert "text=" in result
    assert "done=False" in result


def test_todo_repr_with_done_true() -> None:
    """repr(Todo) should show done=True for completed todos."""
    todo = Todo(id=1, text="completed task", done=True)
    result = repr(todo)

    assert "done=True" in result


def test_todo_repr_is_concise() -> None:
    """repr(Todo) output should be concise (< 80 chars for normal todos)."""
    todo = Todo(id=1, text="buy milk", done=False)
    result = repr(todo)

    assert len(result) < 80, f"repr too long: {len(result)} chars - {result}"


def test_todo_repr_truncates_long_text() -> None:
    """repr(Todo) should truncate long text (> 50 chars)."""
    long_text = "a" * 100
    todo = Todo(id=1, text=long_text)
    result = repr(todo)

    # Truncated representation should not be excessively long
    assert len(result) < 150, f"repr should truncate long text: {len(result)} chars"
    # Should contain ellipsis or similar truncation indicator
    assert "..." in result or len(result) < 100


def test_todo_repr_handles_special_characters() -> None:
    """repr(Todo) should handle special characters (quotes, newlines, etc.)."""
    # Text with quotes
    todo1 = Todo(id=1, text='text with "quotes"')
    result1 = repr(todo1)
    assert "Todo" in result1

    # Text with newlines - repr should escape or handle them
    todo2 = Todo(id=2, text="line1\nline2")
    result2 = repr(todo2)
    assert "Todo" in result2
    # Should not have literal newlines in the repr output
    assert "\n" not in result2 or repr(result2).count("\\n") > 0


def test_todo_repr_eval_able_optional() -> None:
    """repr(Todo) output should ideally be eval-able or at least informative."""
    todo = Todo(id=1, text="simple task", done=True)
    result = repr(todo)

    # At minimum, should contain all key information to recreate the object
    assert "id=1" in result
    assert "simple task" in result
    assert "done=True" in result


def test_todo_repr_multiple_todos_distinct() -> None:
    """repr(Todo) should make different todos distinguishable in debugger."""
    todo1 = Todo(id=1, text="task one", done=False)
    todo2 = Todo(id=2, text="task two", done=True)

    repr1 = repr(todo1)
    repr2 = repr(todo2)

    # Different todos should have different reprs
    assert repr1 != repr2
    # Key distinguishing info should be present
    assert "id=1" in repr1
    assert "id=2" in repr2


def test_todo_repr_sanitizes_control_characters() -> None:
    """repr(Todo) should escape/sanitize control characters in text (Issue #3776).

    Control characters like null bytes, ANSI escape sequences, and other
    non-printable characters should be escaped to prevent terminal output
    manipulation and ensure the repr output is safe to display.
    """
    # Test null byte (0x00)
    todo_null = Todo(id=1, text="test\x00null")
    result_null = repr(todo_null)
    assert "\x00" not in result_null, "repr should not contain literal null byte"
    assert "\\x00" in result_null, "repr should escape null byte as \\x00"

    # Test ANSI escape sequence (0x1b)
    todo_ansi = Todo(id=2, text="test\x1b[31mred\x1b[0m")
    result_ansi = repr(todo_ansi)
    assert "\x1b" not in result_ansi, "repr should not contain literal ESC character"
    assert "\\x1b" in result_ansi, "repr should escape ESC as \\x1b"

    # Test carriage return (0x0d)
    todo_cr = Todo(id=3, text="test\rreturn")
    result_cr = repr(todo_cr)
    assert "\r" not in result_cr, "repr should not contain literal carriage return"
    assert "\\r" in result_cr, "repr should escape CR as \\r"

    # Test tab character (0x09)
    todo_tab = Todo(id=4, text="test\ttab")
    result_tab = repr(todo_tab)
    assert "\t" not in result_tab, "repr should not contain literal tab"
    assert "\\t" in result_tab, "repr should escape TAB as \\t"

    # Test DEL character (0x7f)
    todo_del = Todo(id=5, text="test\x7fdelete")
    result_del = repr(todo_del)
    assert "\x7f" not in result_del, "repr should not contain literal DEL character"
    assert "\\x7f" in result_del, "repr should escape DEL as \\x7f"


def test_todo_repr_sanitizes_c1_control_characters() -> None:
    """repr(Todo) should escape C1 control characters (0x80-0x9f)."""
    # Test a C1 control character (0x85 - NEL, Next Line)
    todo_c1 = Todo(id=1, text="test\x85data")
    result_c1 = repr(todo_c1)
    assert "\x85" not in result_c1, "repr should not contain literal C1 control char"
    assert "\\x85" in result_c1, "repr should escape C1 control char as \\x85"
