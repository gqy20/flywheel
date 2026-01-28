"""Test for Issue #599: Incomplete sanitization logic for tags

This test ensures that the sanitize_tags function properly handles:
1. Shell metacharacters (already covered)
2. JSON-injection characters (quotes, backslashes, etc.)
3. Other characters that could cause issues with storage backends
"""

import pytest

from flywheel.cli import sanitize_tags


class TestTagSanitization:
    """Test tag sanitization for security issues (Issue #599)."""

    def test_shell_metacharacters_are_removed(self):
        """Test that shell metacharacters are removed from tags."""
        # Test various shell metacharacters
        assert sanitize_tags("tag;with;semicolons") == ["tagwithsemicolons"]
        assert sanitize_tags("tag|with|pipes") == ["tagwithpipes"]
        assert sanitize_tags("tag&with&ampersands") == ["tagwithampersands"]
        assert sanitize_tags("tag`with`backticks") == ["tagwithbackticks"]
        assert sanitize_tags("tag$with$dollars") == ["tagwithdollars"]
        assert sanitize_tags("tag(with)parentheses") == ["tagwithparentheses"]
        assert sanitize_tags("tag\\with\\backslashes") == ["tagwithbackslashes"]
        assert sanitize_tags("tag<with>anglebrackets") == ["tagwithanglebrackets"]

    def test_newline_and_null_bytes_are_removed(self):
        """Test that newlines and null bytes are removed from tags."""
        assert sanitize_tags("tag\nwith\nnewlines") == ["tagwithnewlines"]
        assert sanitize_tags("tag\rwith\rcarriage") == ["tagwithcarriage"]
        assert sanitize_tags("tag\x00with\x00nulls") == ["tagwithnulls"]

    def test_json_injection_characters_are_handled(self):
        """Test that JSON-injection characters are properly handled.

        This is the main fix for Issue #599. While the current code removes
        shell metacharacters, it doesn't handle characters that could cause
        JSON injection or corruption when stored in JSON format.
        """
        # Double quotes can break JSON structure
        result = sanitize_tags('tag"with"quotes')
        assert result == ["tagwithquotes"], f"Double quotes should be removed, got {result}"

        # Single quotes should also be handled (though less dangerous in JSON)
        result = sanitize_tags("tag'with'apostrophes")
        assert result == ["tagwithapostrophes"], f"Single quotes should be removed, got {result}"

        # Multiple types of problematic characters together
        result = sanitize_tags('tag";with&`mix$ed\\chars')
        assert result == ["tagwithmixedchars"], f"Mixed dangerous chars should be removed, got {result}"

    def test_empty_tags_after_sanitization_are_filtered(self):
        """Test that tags that become empty after sanitization are filtered out."""
        result = sanitize_tags(";;;",)
        assert result == [], "Tags that become empty after sanitization should be filtered"

        result = sanitize_tags("tag1,;;,tag2")
        assert result == ["tag1", "tag2"], "Only non-empty tags should be returned"

    def test_whitespace_handling(self):
        """Test that whitespace is properly handled."""
        assert sanitize_tags("  tag1  ,  tag2  ") == ["tag1", "tag2"]
        assert sanitize_tags("tag1, tag2") == ["tag1", "tag2"]

    def test_normal_tags_are_preserved(self):
        """Test that normal tags are preserved correctly."""
        assert sanitize_tags("work,personal,urgent") == ["work", "personal", "urgent"]
        assert sanitize_tags("bug-fix,feature-request") == ["bugfix", "featurerequest"]

    def test_empty_input_returns_empty_list(self):
        """Test that empty input returns empty list."""
        assert sanitize_tags(None) == []
        assert sanitize_tags("") == []
        assert sanitize_tags("   ") == []

    def test_complex_injection_attempts(self):
        """Test complex injection attempts that could compromise storage."""
        # JSON injection attempt
        malicious = '{"title":"hacked","id":999}'
        result = sanitize_tags(malicious)
        assert result == ["titlehackedid999"], f"JSON structure chars should be removed, got {result}"

        # Command injection with backticks
        malicious = '`rm -rf /`'
        result = sanitize_tags(malicious)
        assert result == ["rm -rf "], f"Backticks should be removed, got {result}"

        # Path traversal attempt
        malicious = '../../../etc/passwd'
        result = sanitize_tags(malicious)
        assert result == ["..etcpasswd"], f"Path traversal chars should be handled, got {result}"

    def test_unicode_and_special_chars(self):
        """Test that Unicode and other special characters are handled properly."""
        # Unicode characters should be allowed (they're safe in JSON)
        assert sanitize_tags("标签,日本語,🎯") == ["标签", "日本語", "🎯"]

        # Emojis should be preserved
        assert sanitize_tags("bug,🐛,feature,✨") == ["bug", "🐛", "feature", "✨"]

        # But combined with dangerous chars, the dangerous ones should be removed
        result = sanitize_tags("bug🐛;feature✨")
        assert result == ["bug🐛feature✨"], f"Dangerous chars in unicode should be removed, got {result}"
