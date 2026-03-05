"""Tests for Todo.__repr__ quote escaping (Issue #7301).

These tests verify that:
1. Todo with text containing quotes produces valid repr output
2. Truncated text with quotes at truncation boundary does not produce malformed repr
3. repr output is always valid Python that can be parsed
"""

from __future__ import annotations

import ast

from flywheel.todo import Todo


def test_todo_repr_with_quotes_in_short_text() -> None:
    """Todo with text containing quotes should produce valid repr output."""
    todo = Todo(id=1, text='He said "hello"')
    result = repr(todo)

    # repr should be parseable Python
    ast.parse(result, mode="eval")

    # Should contain the quote character in a properly escaped form
    assert "hello" in result


def test_todo_repr_with_single_quotes_in_text() -> None:
    """Todo with single quotes in text should produce valid repr."""
    todo = Todo(id=1, text="It's a nice day")
    result = repr(todo)

    # repr should be parseable Python
    ast.parse(result, mode="eval")


def test_todo_repr_with_quotes_near_truncation_boundary() -> None:
    """Truncated text with quotes near position 47 should not produce malformed repr."""
    # Create text where quotes appear near the truncation boundary (position 47)
    long_text_with_quotes = "a" * 45 + '"quoted"' + "b" * 20
    todo = Todo(id=1, text=long_text_with_quotes)
    result = repr(todo)

    # repr should be parseable Python
    ast.parse(result, mode="eval")

    # Should not break the string format
    assert result.startswith("Todo(")
    assert result.endswith(")")


def test_todo_repr_with_mixed_quotes_in_long_text() -> None:
    """Long text with both single and double quotes should produce valid repr."""
    long_text = "Text with \"double\" and 'single' quotes " * 3
    todo = Todo(id=1, text=long_text)
    result = repr(todo)

    # repr should be parseable Python
    ast.parse(result, mode="eval")


def test_todo_repr_with_backslash_in_long_text() -> None:
    """Long text with backslashes should produce valid repr."""
    long_text = "Path\\to\\file\\with\\backslashes " * 5
    todo = Todo(id=1, text=long_text)
    result = repr(todo)

    # repr should be parseable Python
    ast.parse(result, mode="eval")


def test_todo_repr_with_newlines_in_long_text() -> None:
    """Long text with newlines should produce valid repr without literal newlines."""
    long_text = "Line1\nLine2\nLine3\n" * 10
    todo = Todo(id=1, text=long_text)
    result = repr(todo)

    # repr should be parseable Python
    ast.parse(result, mode="eval")

    # Should not contain literal newlines (they should be escaped)
    assert "\n" not in result or "\\n" in result


def test_todo_repr_truncation_does_not_break_python_syntax() -> None:
    """Ensure truncation never produces malformed Python syntax."""
    # Test various character sequences that could potentially break repr
    problematic_texts = [
        '"' * 100,  # Many double quotes
        "'" * 100,  # Many single quotes
        "\\" * 100,  # Many backslashes
        "\n" * 100,  # Many newlines
        '"' + "a" * 100,  # Quote at start then long text
        "a" * 100 + '"',  # Long text then quote at end
        "a" * 46 + '"' + "b" * 100,  # Quote at truncation boundary
    ]

    for text in problematic_texts:
        todo = Todo(id=1, text=text)
        result = repr(todo)

        # Each repr should be valid Python syntax
        try:
            ast.parse(result, mode="eval")
        except SyntaxError as e:
            raise AssertionError(f"Invalid Python syntax in repr: {result!r}") from e


def test_todo_repr_is_informative_for_debugging() -> None:
    """repr should remain informative even with truncation."""
    long_text = "This is a very long task description that needs to be truncated"
    todo = Todo(id=1, text=long_text, done=True)
    result = repr(todo)

    # Should include class name
    assert "Todo" in result
    # Should include id
    assert "id=1" in result
    # Should include done status
    assert "done=True" in result
    # Should indicate truncation
    assert "..." in result
