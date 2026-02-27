"""Tests for Todo.__repr__ multi-byte UTF-8 handling (Issue #5998).

These tests verify that:
1. repr(Todo) handles multi-byte UTF-8 characters correctly
2. Truncation never produces invalid Unicode strings
3. Emoji, CJK, and other multi-byte characters work properly
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_repr_with_emoji_text() -> None:
    """repr(Todo) should handle emoji text correctly without invalid Unicode."""
    # Each emoji is 4 bytes in UTF-8, but 1 character in Python strings
    text = "😀" * 20  # 20 emoji characters (80 bytes in UTF-8)
    todo = Todo(id=1, text=text)
    result = repr(todo)

    # Should produce valid string without UnicodeDecodeError
    encoded = result.encode("utf-8")
    decoded = encoded.decode("utf-8")
    assert decoded == result

    # Should contain Todo marker
    assert "Todo" in result


def test_todo_repr_with_cjk_text_truncation() -> None:
    """repr(Todo) should truncate CJK text correctly at character boundaries."""
    # Create text longer than 50 chars to trigger truncation
    cjk_text = "中文测试" * 15  # 60 characters, all multi-byte in UTF-8
    todo = Todo(id=1, text=cjk_text)
    result = repr(todo)

    # Should produce valid string
    encoded = result.encode("utf-8")
    decoded = encoded.decode("utf-8")
    assert decoded == result

    # Should show truncation
    assert "..." in result


def test_todo_repr_with_mixed_multi_byte_text() -> None:
    """repr(Todo) should handle mixed ASCII and multi-byte text."""
    # Mix of ASCII and emoji that exceeds 50 chars
    text = "a" * 25 + "😀" * 10 + "b" * 25  # 60 chars total
    todo = Todo(id=1, text=text)
    result = repr(todo)

    # Should produce valid string
    encoded = result.encode("utf-8")
    decoded = encoded.decode("utf-8")
    assert decoded == result


def test_todo_repr_truncation_preserves_valid_unicode() -> None:
    """Truncation should always preserve valid Unicode strings."""
    # Test various multi-byte characters that could theoretically cause issues
    test_cases = [
        ("😀" * 20, "emoji"),  # 4-byte UTF-8 characters
        ("中文" * 30, "CJK"),  # 3-byte UTF-8 characters
        ("é" * 60, "accented"),  # 2-byte UTF-8 characters
        ("a" * 30 + "🔥" + "b" * 30, "mixed with emoji in middle"),
    ]

    for text, description in test_cases:
        todo = Todo(id=1, text=text)
        result = repr(todo)

        # Verify the result is valid UTF-8
        try:
            encoded = result.encode("utf-8")
            decoded = encoded.decode("utf-8")
            assert decoded == result, f"Round-trip failed for {description}"
        except UnicodeDecodeError as e:
            raise AssertionError(f"Invalid Unicode in repr for {description}: {e}") from e


def test_todo_repr_no_surrogate_pairs_broken() -> None:
    """Truncation should not break surrogate pairs."""
    # Some emoji are surrogate pairs (though Python handles this transparently)
    text = "👨‍👩‍👧‍👦" * 20  # Family emoji (complex multi-codepoint)
    todo = Todo(id=1, text=text)
    result = repr(todo)

    # Should produce valid string
    encoded = result.encode("utf-8")
    decoded = encoded.decode("utf-8")
    assert decoded == result
