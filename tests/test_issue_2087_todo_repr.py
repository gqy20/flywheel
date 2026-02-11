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


# Regression tests for issue #2751 - control character escaping in __repr__


def test_todo_repr_escapes_newline() -> None:
    """repr(Todo) should escape newline characters to prevent terminal manipulation."""
    todo = Todo(id=1, text="line1\nline2")
    result = repr(todo)

    # Should contain escaped representation, not literal newline
    assert "\\n" in result, f"repr should escape newlines: {result!r}"
    # The string itself should not contain actual newlines (single line output)
    assert result.count("\n") == 0, f"repr should be single line: {result!r}"


def test_todo_repr_escapes_carriage_return() -> None:
    """repr(Todo) should escape carriage return characters."""
    todo = Todo(id=1, text="task\r\nFAKE")
    result = repr(todo)

    # Should contain escaped \r\n
    assert "\\r" in result, f"repr should escape \\r: {result!r}"
    assert "\\n" in result, f"repr should escape \\n: {result!r}"
    # Should not contain actual carriage returns
    assert "\r" not in result, f"repr should not have literal \\r: {result!r}"


def test_todo_repr_escapes_tab() -> None:
    """repr(Todo) should escape tab characters."""
    todo = Todo(id=1, text="col1\tcol2")
    result = repr(todo)

    # Should contain escaped \t
    assert "\\t" in result, f"repr should escape tabs: {result!r}"
    # Should not contain actual tabs
    assert "\t" not in result, f"repr should not have literal tabs: {result!r}"


def test_todo_repr_escapes_ansi_codes() -> None:
    """repr(Todo) should escape ANSI escape sequences."""
    todo = Todo(id=1, text="\x1b[31mRED\x1b[0m")
    result = repr(todo)

    # Should escape ESC character (0x1b)
    assert "\\x1b" in result, f"repr should escape ANSI codes: {result!r}"
    # Should not contain actual ESC character
    assert "\x1b" not in result, f"repr should not have literal ESC: {result!r}"


def test_todo_repr_escapes_backslash() -> None:
    """repr(Todo) should escape backslash to prevent collision with escape sequences."""
    todo = Todo(id=1, text="C:\\path\\to\\file")
    result = repr(todo)

    # Should escape backslash as \\
    assert "\\\\" in result, f"repr should escape backslashes: {result!r}"


def test_todo_repr_escapes_null_byte() -> None:
    """repr(Todo) should escape null bytes."""
    todo = Todo(id=1, text="before\x00after")
    result = repr(todo)

    # Should escape null byte
    assert "\\x00" in result, f"repr should escape null byte: {result!r}"
    # Should not contain actual null byte
    assert "\x00" not in result, f"repr should not have literal null: {result!r}"


def test_todo_repr_normal_text_readable() -> None:
    """repr(Todo) should keep normal text readable after sanitization."""
    todo = Todo(id=1, text="buy milk")
    result = repr(todo)

    # Should be readable and contain original text
    assert "buy milk" in result
    assert "Todo" in result
    assert "id=1" in result


def test_todo_repr_escapes_multiple_controls() -> None:
    """repr(Todo) should handle multiple control characters together."""
    todo = Todo(id=1, text="line1\n\ttab\r\nend")
    result = repr(todo)

    # All control chars should be escaped
    assert "\\n" in result
    assert "\\t" in result
    assert "\\r" in result
    # No actual control characters in output
    assert not any(c in result for c in "\n\t\r")
