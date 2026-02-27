"""Tests for Todo.__repr__ UTF-8 safe truncation (Issue #5998).

These tests verify that:
1. repr(Todo) handles multi-byte UTF-8 characters (emoji, CJK) correctly
2. Truncation doesn't produce invalid Unicode sequences
3. No UnicodeDecodeError occurs when repr output is encoded/decoded
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_repr_with_emoji_truncation() -> None:
    """repr(Todo) should truncate emoji strings without breaking Unicode."""
    # 20 emojis = 20 characters, but 80 bytes in UTF-8
    emoji_text = "😀" * 20
    todo = Todo(id=1, text=emoji_text)
    result = repr(todo)

    # Should be valid Unicode that can be encoded and decoded
    encoded = result.encode("utf-8")
    decoded = encoded.decode("utf-8")
    assert decoded == result

    # Should contain truncation indicator
    assert "..." in result or len(result) < 100


def test_todo_repr_with_cjk_truncation() -> None:
    """repr(Todo) should truncate CJK (Chinese/Japanese/Korean) strings correctly."""
    # 60 CJK characters = 60 characters, but 180 bytes in UTF-8
    cjk_text = "中" * 60
    todo = Todo(id=1, text=cjk_text)
    result = repr(todo)

    # Should be valid Unicode
    encoded = result.encode("utf-8")
    decoded = encoded.decode("utf-8")
    assert decoded == result

    # Should contain truncation indicator since > 50 chars
    assert "..." in result


def test_todo_repr_with_mixed_multibyte_truncation() -> None:
    """repr(Todo) should handle mixed ASCII and multi-byte characters."""
    # Mix of ASCII and multi-byte characters that exceeds 50 chars
    mixed_text = "Task: " + "🎉" * 15  # 6 + 15 = 21 chars, but more bytes
    todo = Todo(id=1, text=mixed_text)
    result = repr(todo)

    # Should be valid Unicode
    encoded = result.encode("utf-8")
    decoded = encoded.decode("utf-8")
    assert decoded == result


def test_todo_repr_no_unicode_error_on_print() -> None:
    """repr(Todo) should not raise UnicodeError when printed to terminal."""
    # Long text with emojis that will be truncated
    text_with_emoji = "Important task 🚀🎯💡🔥⚡" * 5  # Well over 50 chars
    todo = Todo(id=1, text=text_with_emoji)

    # This should not raise any Unicode-related errors
    result = repr(todo)

    # Verify it's a valid string
    assert isinstance(result, str)

    # Verify we can encode it to UTF-8 (what terminals typically use)
    result.encode("utf-8")


def test_todo_repr_truncation_preserves_valid_utf8() -> None:
    """Truncated repr output should always be valid UTF-8."""
    # Various multi-byte character strings that will be truncated
    test_cases = [
        "😀" * 100,  # 4-byte emoji characters
        "中" * 100,  # 3-byte CJK characters
        "ע" * 100,  # 2-byte Hebrew characters
        "a" * 25 + "🎉" * 20,  # Mixed ASCII and emoji
    ]

    for text in test_cases:
        todo = Todo(id=1, text=text)
        result = repr(todo)

        # Must be encodable as UTF-8 without errors
        encoded = result.encode("utf-8")
        # Must be decodable back to the same string
        decoded = encoded.decode("utf-8")
        assert decoded == result, f"Round-trip failed for text starting with: {text[:20]}"
