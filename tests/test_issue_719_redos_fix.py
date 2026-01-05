"""Tests for Issue #719 - ReDoS prevention in sanitize_string.

This test verifies that the hyphen character in the regex character class
is properly placed at the end to prevent ReDoS (Regular Expression Denial of Service)
attacks through unintended range interpretation.

The hyphen should be at the end of the character class (e.g., [{}-]) rather
than in the middle where it could be interpreted as a range operator (e.g., [-{}]).
"""

import pytest
from flywheel.cli import sanitize_string


class TestHyphenInCharacterClass:
    """Test that hyphens are safely removed without ReDoS risk."""

    def test_hyphen_is_removed(self):
        """Test that hyphen characters are properly removed from input."""
        # Single hyphen
        assert sanitize_string("test-value") == "testvalue"

        # Multiple hyphens
        assert sanitize_string("test-value-with-hyphens") == "testvaluewithhyphens"

        # Hyphen at various positions
        assert sanitize_string("-test") == "test"
        assert sanitize_string("test-") == "test"
        assert sanitize_string("-test-") == "test"

    def test_hyphen_with_other_dangerous_chars(self):
        """Test that hyphens are removed alongside other dangerous characters."""
        # Combination of dangerous characters including hyphen
        assert sanitize_string("test;value-with|chars") == "testvaluewithchars"
        assert sanitize_string("a-b;c|d&e`f$g(h)i<j>k{l}m") == "abcdefghijklm"

    def test_no_unintended_range_interpretation(self):
        """Test that hyphen doesn't cause unintended range matching.

        This test ensures that the hyphen in the character class is placed
        at the end (or beginning) and not interpreted as a range operator.

        For example, [{}-] should match: {, }, and -
        It should NOT match the range between } and - (which would be invalid)
        """
        # Test characters that might be in a range if hyphen is misplaced
        # With hyphen at the end: [{}-] matches {, }, -
        # We expect all of these to be removed

        # Test that specific special chars are removed
        assert sanitize_string("test{value}end-dash") == "testvalueenddash"
        assert sanitize_string("a{b}c-d") == "abcd"

    def test_preservation_of_safe_content(self):
        """Test that safe content is preserved while hyphens are removed."""
        # Preserve quotes, brackets, etc.
        assert sanitize_string('test "value" with \'quotes\'') == 'test "value" with \'quotes\''
        assert sanitize_string("test [value] (brackets)") == "test [value] brackets"

        # But remove hyphens
        assert sanitize_string("test-value [bracket]") == "testvalue [bracket]"

    def test_edge_cases(self):
        """Test edge cases for hyphen removal."""
        # Empty string
        assert sanitize_string("") == ""

        # Only hyphens
        assert sanitize_string("---") == ""

        # Mixed with spaces (spaces are preserved)
        assert sanitize_string("test - value") == "test  value"

    def test_performance_with_long_input(self):
        """Test that the function handles long input without ReDoS issues.

        This test verifies that the regex doesn't cause catastrophic backtracking
        even with long input strings containing hyphens and other special chars.
        """
        # Create a long string with repeating pattern including hyphens
        long_input = "a-b" * 1000  # 3000 characters

        # Should complete quickly without ReDoS
        result = sanitize_string(long_input)
        assert result == "ab" * 1000
        assert len(result) == 2000
