"""Tests for Issue #804 - Overly aggressive character filtering.

Issue #804 points out that the current implementation removes ALL non-Latin-script
characters (Cyrillic, CJK, Arabic, etc.) to prevent visual homograph attacks.
However, this is overly aggressive for general text input like todo titles and
descriptions, where international users should be able to use their native scripts.

The fix should:
1. Remove the blanket ban on non-Latin scripts
2. Still preserve security by removing dangerous shell metacharacters and control chars
3. Let international users use Cyrillic, CJK, Arabic, etc. in their todos
"""

import pytest
from flywheel.cli import sanitize_string


class TestIssue804:
    """Test that sanitize_string preserves legitimate international content."""

    def test_sanitize_string_preserves_cyrillic(self):
        """Test that Cyrillic characters are preserved in general usage.

        Issue #804: Russian users should be able to write todos in Russian.
        The current implementation incorrectly removes all Cyrillic characters.
        """
        # Russian text: "Привет мир" (Hello world)
        input_text = "Привет мир"
        result = sanitize_string(input_text)
        # Current implementation removes all Cyrillic, but it should be preserved
        # for general text input (not filenames or shell parameters)
        assert result == "Привет мир", f"Expected 'Привет мир', got '{result}'"

    def test_sanitize_string_preserves_cjk(self):
        """Test that CJK characters are preserved in general usage."""
        # Japanese text: "こんにちは世界" (Hello world)
        input_text = "こんにちは世界"
        result = sanitize_string(input_text)
        # Should preserve Japanese text
        assert result == "こんにちは世界", f"Expected 'こんにちは世界', got '{result}'"

    def test_sanitize_string_preserves_chinese(self):
        """Test that Chinese characters are preserved in general usage."""
        # Chinese text: "你好世界" (Hello world)
        input_text = "你好世界"
        result = sanitize_string(input_text)
        # Should preserve Chinese text
        assert result == "你好世界", f"Expected '你好世界', got '{result}'"

    def test_sanitize_string_preserves_arabic(self):
        """Test that Arabic characters are preserved in general usage."""
        # Arabic text: "مرحبا بالعالم" (Hello world)
        input_text = "مرحبا بالعالم"
        result = sanitize_string(input_text)
        # Should preserve Arabic text
        assert result == "مرحبا بالعالم", f"Expected 'مرحبا بالعالم', got '{result}'"

    def test_sanitize_string_still_removes_dangerous_chars(self):
        """Test that dangerous shell metacharacters are still removed."""
        # Even with international characters, dangerous metacharacters should be removed
        input_text = "Привет; мир"
        result = sanitize_string(input_text)
        # Semicolon should be removed, but Cyrillic preserved
        assert result == "Привет мир", f"Expected 'Привет мир', got '{result}'"

    def test_sanitize_string_preserves_latin_with_accents(self):
        """Test that Latin-script accented characters are preserved."""
        # French text: "Café au lait"
        input_text = "Café au lait"
        result = sanitize_string(input_text)
        assert result == "Café au lait", f"Expected 'Café au lait', got '{result}'"

    def test_sanitize_string_preserves_mixed_content(self):
        """Test that mixed content is handled correctly."""
        # English + Japanese + dangerous chars
        input_text = "Task: タスク done | remove"
        result = sanitize_string(input_text)
        # Should preserve text but remove pipe
        assert result == "Task: タスク done remove", f"Expected 'Task: タスク done remove', got '{result}'"
