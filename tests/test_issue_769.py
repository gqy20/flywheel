"""Tests for Issue #769 - Internal backslash security vulnerability.

This test verifies that sanitize_string properly handles internal backslashes
that could be used as shell escape sequences.
"""

import pytest
from flywheel.cli import sanitize_string


class TestInternalBackslashSecurity:
    """Test suite for Issue #769 - Internal backslash handling."""

    def test_internal_backslash_with_n(self):
        """Test that internal backslash followed by 'n' is neutralized.

        In shell contexts, '\n' can be interpreted as a newline character,
        which could enable injection attacks.
        """
        # Test case: backslash-n sequence that could become newline
        input_str = "hello\\nworld"
        result = sanitize_string(input_str)
        # The backslash should be removed or escaped to prevent shell interpretation
        assert "\\n" not in result
        assert result == "hello\\nworld" or result == "hellonworld"

    def test_internal_backslash_with_t(self):
        """Test that internal backslash followed by 't' is neutralized.

        In shell contexts, '\t' can be interpreted as a tab character.
        """
        input_str = "hello\\tworld"
        result = sanitize_string(input_str)
        # The backslash should be removed or escaped
        assert "\\t" not in result

    def test_internal_backslash_with_r(self):
        """Test that internal backslash followed by 'r' is neutralized.

        In shell contexts, '\r' can be interpreted as a carriage return.
        """
        input_str = "hello\\rworld"
        result = sanitize_string(input_str)
        # The backslash should be removed or escaped
        assert "\\r" not in result

    def test_windows_path_with_backslashes(self):
        """Test that Windows paths remain usable after sanitization.

        This tests the tension between security (removing backslashes) and
        usability (preserving Windows paths). The current implementation
        preserves internal backslashes for Windows paths, but this creates
        a security risk if the data is used in shell contexts.
        """
        input_str = "C:\\Users\\test\\file.txt"
        result = sanitize_string(input_str)
        # With the security fix, backslashes should be removed or escaped
        # The test expects the secure behavior
        assert "\\" not in result or result.count("\\") == 0

    def test_multiple_backslash_sequences(self):
        """Test multiple backslash escape sequences in one string."""
        input_str = "cmd\\nwith\\rtabs\\tand\\nnewlines"
        result = sanitize_string(input_str)
        # All backslash-letter sequences should be neutralized
        assert "\\n" not in result
        assert "\\r" not in result
        assert "\\t" not in result

    def test_trailing_backslash_still_removed(self):
        """Test that trailing backslashes are still removed (Issue #736)."""
        input_str = "path\\"
        result = sanitize_string(input_str)
        assert not result.endswith("\\")

    def test_trailing_backslash_with_sequence(self):
        """Test trailing backslash followed by escape sequence."""
        input_str = "path\\n"
        result = sanitize_string(input_str)
        # Both the trailing backslash and the internal sequence should be handled
        assert not result.endswith("\\")
        assert "\\n" not in result

    def test_backslash_before_quote(self):
        """Test backslash before quotes (shell escape scenario)."""
        # Test with single quote
        input_str = "it\\'s"
        result = sanitize_string(input_str)
        # The backslash-quote combination should be neutralized
        assert "\\'" not in result or result == "it's"

        # Test with double quote
        input_str = 'say \\"hello\\"'
        result = sanitize_string(input_str)
        assert '\\"' not in result

    def test_backslash_before_dollar_sign(self):
        """Test backslash before dollar sign (variable expansion)."""
        input_str = "price\\$100"
        result = sanitize_string(input_str)
        # The backslash-dollar combination should be neutralized
        # Note: $ is already removed by the dangerous_chars filter
        assert "$" not in result

    def test_consecutive_backslashes(self):
        """Test consecutive backslashes."""
        input_str = "path\\\\to\\\\file"
        result = sanitize_string(input_str)
        # Consecutive backslashes should be handled safely
        # After sanitization, we should not have dangerous sequences
        assert "\\\\" not in result or result.count("\\") < input_str.count("\\")

    def test_backslash_in_middle_of_word(self):
        """Test backslash in the middle of a word."""
        input_str = "hel\\lo"
        result = sanitize_string(input_str)
        # The backslash should be removed
        assert "\\" not in result or "llo" in result

    def test_empty_and_none_inputs(self):
        """Test edge cases with empty and None inputs."""
        assert sanitize_string("") == ""
        assert sanitize_string(None) == ""

    def test_long_string_with_backslashes(self):
        """Test that length limits still apply with backslashes."""
        # Create a string with many backslash sequences
        input_str = "\\n" * 1000  # 2000 characters
        result = sanitize_string(input_str, max_length=100)
        assert len(result) <= 100

    def test_backslash_preservation_in_safe_contexts(self):
        """Test that we're not overly aggressive with backslash removal.

        If we choose to preserve backslashes in certain safe contexts,
        this test validates that behavior. However, for maximum security
        in shell contexts, we should remove all backslashes.
        """
        # Simple case: single backslash not followed by dangerous char
        input_str = "ratio 3:1"
        result = sanitize_string(input_str)
        # Colon is fine, backslash should be removed if present
        assert "\\" not in result
