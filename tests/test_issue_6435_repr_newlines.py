"""Tests for Todo.__repr__ newline handling (Issue #6435).

These tests verify that:
1. repr output contains no literal newline characters
2. repr output is single-line for any text content
3. Truncated text with newlines still escapes properly
4. Various control characters are properly escaped
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_no_literal_newline() -> None:
    """repr should not contain literal newline characters."""
    todo = Todo(id=1, text="line1\nline2")
    result = repr(todo)
    assert "\n" not in result, f"repr should not contain literal newline: {result!r}"


def test_repr_single_line_output() -> None:
    """repr output should be single-line for any text content."""
    todo = Todo(id=1, text="a\nb\nc\nd\ne")
    result = repr(todo)
    assert result.count("\n") == 0, (
        f"repr should be single-line but has {result.count(chr(10))} newlines: {result!r}"
    )


def test_repr_truncated_text_with_newline() -> None:
    """Truncated text with newline should still escape properly."""
    # Create text that will be truncated (> 50 chars)
    text = "a" * 46 + "\n" + "b" * 20
    todo = Todo(id=1, text=text)
    result = repr(todo)
    assert "\n" not in result, f"Truncated repr should not contain literal newline: {result!r}"


def test_repr_various_control_characters() -> None:
    """repr should escape various control characters (tab, CR, etc.)."""
    test_cases = [
        ("tab", "a\tb"),
        ("carriage return", "a\rb"),
        ("null", "a\x00b"),
        ("bell", "a\x07b"),
        ("escape", "a\x1bb"),
        ("vertical tab", "a\x0bb"),
        ("form feed", "a\x0cb"),
        ("backspace", "a\x08b"),
        ("mixed", "a\n\t\r\x00b"),
    ]

    for name, text in test_cases:
        todo = Todo(id=1, text=text)
        result = repr(todo)
        # Check for any unescaped control characters (0x00-0x1f)
        for char in result:
            if ord(char) < 0x20:
                raise AssertionError(f"Unescaped control character in repr for {name}: {result!r}")


def test_repr_newline_at_truncation_boundary() -> None:
    """Test newline exactly at truncation boundary."""
    # 50 chars exactly - no truncation
    text_no_truncate = "a" * 49 + "\n"
    todo = Todo(id=1, text=text_no_truncate)
    result = repr(todo)
    assert "\n" not in result

    # 51 chars - will be truncated
    text_truncate = "a" * 50 + "\n"
    todo = Todo(id=2, text=text_truncate)
    result = repr(todo)
    assert "\n" not in result


def test_repr_many_newlines() -> None:
    """Test text with many newlines."""
    text = "\n" * 30
    todo = Todo(id=1, text=text)
    result = repr(todo)
    assert "\n" not in result
    # Verify it shows escaped newlines
    assert "\\n" in result or repr(result).count("\\n") > 0
