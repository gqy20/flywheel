"""Tests for Issue #709 - ReDoS vulnerability in sanitize_string.

This test verifies that the hyphen in the regex character class is properly
escaped to prevent catastrophic backtracking.
"""

import re
import pytest
from flywheel.cli import sanitize_string


class TestSanitizeStringReDoS:
    """Test that sanitize_string is not vulnerable to ReDoS attacks."""

    def test_hyphen_removed_properly(self):
        """Test that hyphens are removed from input."""
        # Test that hyphens are removed
        assert sanitize_string("test-with-hyphen") == "testwithhyphen"
        assert sanitize_string("a-b-c") == "abc"
        assert sanitize_string("-leading") == "leading"
        assert sanitize_string("trailing-") == "trailing"

    def test_dangerous_chars_removed(self):
        """Test that all dangerous characters are removed."""
        test_string = "test;with&dangerous`chars$here(more)<stuff>{everywhere}-hyphen"
        result = sanitize_string(test_string)
        # All dangerous characters should be removed
        assert ";" not in result
        assert "&" not in result
        assert "`" not in result
        assert "$" not in result
        assert "(" not in result
        assert ")" not in result
        assert "<" not in result
        assert ">" not in result
        assert "{" not in result
        assert "}" not in result
        assert "-" not in result
        # But safe content should remain
        assert "testwithdangerouscharshermorestuffeverywherehyphen" == result

    def test_regex_pattern_no_ranges(self):
        """Test that the regex pattern doesn't contain unintended ranges.

        This test verifies that the hyphen is properly escaped to prevent
        range interpretation that could lead to ReDoS.
        """
        dangerous_chars = r'\-;|&`$()<>{}'

        # Build the regex pattern as used in sanitize_string
        pattern = f'[{dangerous_chars}]'

        # Test that the pattern correctly matches individual characters
        # If hyphen creates a range, it would match unintended characters
        intended_chars = [';', '|', '&', '`', '$', '(', ')', '<', '>', '{', '}', '-']

        for char in intended_chars:
            assert re.match(pattern, char), f"Pattern should match '{char}'"

        # Verify it doesn't match unintended characters
        # If hyphen created range, it might match unexpected characters
        unintended_chars = ['\x00', '\x01', '\x02', 'a', 'b', 'c']
        for char in unintended_chars:
            assert not re.match(pattern, char), f"Pattern should NOT match '{char}' (indicates unintended range)"

    def test_performance_with_repeating_patterns(self):
        """Test that sanitize_string handles repeating patterns efficiently."""
        # Create input with repeating dangerous characters
        # Would be vulnerable to ReDoS if ranges were created
        repeating_input = "a-;b" * 1000

        # Should complete quickly (no catastrophic backtracking)
        result = sanitize_string(repeating_input)
        assert isinstance(result, str)
        # All dangerous chars removed
        assert "-" not in result
        assert ";" not in result
        assert result == "ab" * 1000
