"""Tests for Todo.__repr__ with multi-byte UTF-8 characters (Issue #5998).

These tests verify that:
1. repr(Todo) with multi-byte UTF-8 text produces valid UTF-8 strings
2. No UnicodeDecodeError or invalid byte sequences in repr output
3. Truncation doesn't break multi-byte characters
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_repr_with_emoji_truncation_produces_valid_utf8() -> None:
    """repr(Todo) with long emoji text should produce valid UTF-8."""
    # 51 emoji characters > 50, so truncation will occur
    text = "😀" * 51
    todo = Todo(id=1, text=text)
    result = repr(todo)

    # Verify it can be encoded and decoded as UTF-8
    encoded = result.encode("utf-8")
    decoded = encoded.decode("utf-8")
    assert decoded == result

    # Verify no UnicodeDecodeError
    assert "Todo" in result
    assert "..." in result  # Truncation indicator


def test_repr_with_cjk_truncation_produces_valid_utf8() -> None:
    """repr(Todo) with long CJK text should produce valid UTF-8."""
    # 60 CJK characters > 50, so truncation will occur
    text = "中文测试" * 15  # 60 characters
    todo = Todo(id=1, text=text)
    result = repr(todo)

    # Verify it can be encoded and decoded as UTF-8
    encoded = result.encode("utf-8")
    decoded = encoded.decode("utf-8")
    assert decoded == result

    assert "..." in result


def test_repr_with_flag_emoji_truncation_produces_valid_utf8() -> None:
    """repr(Todo) with flag emoji should produce valid UTF-8."""
    # Flag emoji are 2 code points each
    text = "🇺🇸" * 30  # 60 code points > 50
    todo = Todo(id=1, text=text)
    result = repr(todo)

    # Verify it can be encoded and decoded as UTF-8
    encoded = result.encode("utf-8")
    decoded = encoded.decode("utf-8")
    assert decoded == result

    assert "..." in result


def test_repr_with_skin_tone_emoji_truncation_produces_valid_utf8() -> None:
    """repr(Todo) with skin tone modifier emoji should produce valid UTF-8."""
    # Emoji with skin tone modifier
    text = "👋🏻" * 35  # 70 code points > 50
    todo = Todo(id=1, text=text)
    result = repr(todo)

    # Verify it can be encoded and decoded as UTF-8
    encoded = result.encode("utf-8")
    decoded = encoded.decode("utf-8")
    assert decoded == result

    assert "..." in result


def test_repr_with_zwj_sequence_truncation_produces_valid_utf8() -> None:
    """repr(Todo) with ZWJ sequences should produce valid UTF-8.

    Note: ZWJ sequences like family emoji may be visually broken by truncation,
    but the output should still be valid UTF-8.
    """
    # Family emoji uses ZWJ (Zero Width Joiner)
    text = "👨‍👩‍👧‍👦" * 25  # Many code points > 50
    todo = Todo(id=1, text=text)
    result = repr(todo)

    # Verify it can be encoded and decoded as UTF-8
    encoded = result.encode("utf-8")
    decoded = encoded.decode("utf-8")
    assert decoded == result

    assert "..." in result


def test_repr_with_mixed_ascii_and_emoji_produces_valid_utf8() -> None:
    """repr(Todo) with mixed ASCII and emoji should produce valid UTF-8."""
    text = "Task: " + "😀" * 15  # 6 + 15 = 21, need more
    text = text + " more text here and more " + "🎉" * 10  # Total > 50
    todo = Todo(id=1, text=text)
    result = repr(todo)

    # Verify it can be encoded and decoded as UTF-8
    encoded = result.encode("utf-8")
    decoded = encoded.decode("utf-8")
    assert decoded == result


def test_repr_output_is_printable() -> None:
    """repr(Todo) output should be safely printable to terminals."""
    # Create a todo with various multi-byte characters
    text = "测试Test😀🎉🇺🇸👋🏻👨‍👩‍👧‍👦" * 5
    todo = Todo(id=1, text=text)
    result = repr(todo)

    # Should not raise any exception when printing
    # This verifies the output is valid for terminal display
    try:
        # Encode to UTF-8 and decode back - simulates terminal output
        result.encode("utf-8").decode("utf-8")
    except UnicodeError as e:
        raise AssertionError(f"repr output is not valid UTF-8: {e}") from e
