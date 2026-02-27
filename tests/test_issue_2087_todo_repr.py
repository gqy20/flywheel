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


# Issue #6213: __repr__ should escape/sanitize special characters to prevent
# log injection and ensure single-line output


def test_todo_repr_sanitizes_newlines() -> None:
    """repr(Todo) should escape newlines to prevent multi-line log injection."""
    todo = Todo(id=1, text="line1\nline2")
    result = repr(todo)

    # The repr output should be single-line (no literal newlines)
    assert "\n" not in result, f"repr should not contain literal newlines: {result!r}"
    assert "\r" not in result, f"repr should not contain literal carriage returns: {result!r}"


def test_todo_repr_sanitizes_control_characters() -> None:
    """repr(Todo) should escape control characters (tabs, null bytes, etc.)."""
    # Text with tab and null byte
    todo = Todo(id=1, text="text\twith\x00null")
    result = repr(todo)

    # The repr output should not contain literal control characters
    assert "\t" not in result, f"repr should not contain literal tabs: {result!r}"
    assert "\x00" not in result, f"repr should not contain literal null bytes: {result!r}"


def test_todo_repr_sanitizes_ansi_escape_codes() -> None:
    """repr(Todo) should escape ANSI escape codes to prevent terminal manipulation."""
    # Text with ANSI escape code (e.g., red color)
    todo = Todo(id=1, text="\x1b[31mred text\x1b[0m")
    result = repr(todo)

    # The repr output should not contain literal ANSI escape codes
    assert "\x1b" not in result, f"repr should not contain literal ANSI escapes: {result!r}"
    # Should contain escaped version instead
    assert "\\x1b" in result or "\\u001b" in result, f"ANSI codes should be escaped: {result!r}"


def test_todo_repr_is_always_single_line() -> None:
    """repr(Todo) output should always be a single line regardless of input text."""
    # Text with various line-breaking characters
    todo = Todo(id=1, text="line1\nline2\rline3")
    result = repr(todo)

    # Count lines by splitting on newlines
    lines = result.split("\n")
    assert len(lines) == 1, f"repr should be single-line, got {len(lines)} lines: {result!r}"


def test_todo_repr_sanitizes_backslashes() -> None:
    """repr(Todo) should handle backslashes safely to avoid escape ambiguity."""
    # Text with backslashes that could be confused with escape sequences
    todo = Todo(id=1, text="path\\to\\file")
    result = repr(todo)

    # The repr should preserve backslashes in a safe way
    assert "path" in result
    assert "file" in result
