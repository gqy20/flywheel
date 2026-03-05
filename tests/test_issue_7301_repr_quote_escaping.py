"""Tests for Todo.__repr__ quote escaping (Issue #7301).

These tests verify that:
1. Todo.__repr__ properly escapes quotes in text
2. Truncated text with quotes at truncation boundary produces valid repr
3. repr output is eval-able for debugging purposes
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_escapes_double_quotes_in_short_text() -> None:
    """Todo with short text containing double quotes produces valid repr."""
    todo = Todo(id=1, text='He said "hello"')
    result = repr(todo)

    # Should produce valid Python repr
    assert "Todo" in result
    assert "id=1" in result
    assert "done=False" in result

    # Should be eval-able
    reconstructed = eval(result)
    assert reconstructed.id == 1
    assert reconstructed.text == 'He said "hello"'
    assert reconstructed.done is False


def test_repr_escapes_single_quotes_in_short_text() -> None:
    """Todo with short text containing single quotes produces valid repr."""
    todo = Todo(id=2, text="It's working")
    result = repr(todo)

    # Should produce valid Python repr
    assert "Todo" in result

    # Should be eval-able
    reconstructed = eval(result)
    assert reconstructed.id == 2
    assert reconstructed.text == "It's working"


def test_repr_escapes_mixed_quotes_in_short_text() -> None:
    """Todo with short text containing both quote types produces valid repr."""
    todo = Todo(id=3, text='She said "It\'s great"')
    result = repr(todo)

    # Should be eval-able
    reconstructed = eval(result)
    assert reconstructed.id == 3
    assert reconstructed.text == 'She said "It\'s great"'


def test_repr_truncated_text_with_quotes_near_boundary() -> None:
    """Truncated text with quotes at truncation boundary produces valid repr."""
    # Create text > 50 chars with quotes near position 47 (truncation boundary)
    long_text = "a" * 45 + '"quoted"' + "b" * 50
    todo = Todo(id=4, text=long_text)
    result = repr(todo)

    # Should produce valid Python repr with truncation indicator
    assert "Todo" in result
    assert "..." in result

    # Should be eval-able
    reconstructed = eval(result)
    assert reconstructed.id == 4
    # Text should be truncated with "..." appended
    assert reconstructed.text.endswith("...")
    assert len(reconstructed.text) <= 53  # ~47 chars + "..."


def test_repr_truncated_text_with_double_quote_at_boundary() -> None:
    """Truncated text with double quote exactly at truncation boundary."""
    # Put a double quote right at position 47
    long_text = "a" * 47 + '"' + "b" * 50
    todo = Todo(id=5, text=long_text)
    result = repr(todo)

    # Should be eval-able
    reconstructed = eval(result)
    assert reconstructed.id == 5
    # The truncated text should have quotes properly escaped
    assert reconstructed.text.endswith("...")


def test_repr_truncated_text_with_single_quote_at_boundary() -> None:
    """Truncated text with single quote exactly at truncation boundary."""
    # Put a single quote right at position 47
    long_text = "a" * 47 + "'" + "b" * 50
    todo = Todo(id=6, text=long_text)
    result = repr(todo)

    # Should be eval-able
    reconstructed = eval(result)
    assert reconstructed.id == 6
    assert reconstructed.text.endswith("...")


def test_repr_truncated_text_with_backslash_near_boundary() -> None:
    """Truncated text with backslash near boundary is properly escaped."""
    # Backslash needs special handling in repr
    long_text = "a" * 46 + "\\" + "b" * 50
    todo = Todo(id=7, text=long_text)
    result = repr(todo)

    # Should be eval-able
    reconstructed = eval(result)
    assert reconstructed.id == 7
    # The backslash should be properly escaped in the output
    assert reconstructed.text.endswith("...")


def test_repr_very_long_text_with_many_quotes() -> None:
    """Very long text with many quotes throughout produces valid repr."""
    long_text = '"' + "test" + '"' * 50 + "end"
    todo = Todo(id=8, text=long_text)
    result = repr(todo)

    # Should be eval-able
    reconstructed = eval(result)
    assert reconstructed.id == 8
    assert reconstructed.text.endswith("...")
