"""Test for Issue #694 - Regex escaping security fix."""

import pytest
from flywheel.cli import sanitize_string


class TestRegexEscapingSecurity:
    """Test that the regex pattern in sanitize_string is properly escaped."""

    def test_curly_braces_removed(self):
        """Test that curly braces are properly removed from input."""
        # Test that opening curly brace is removed
        assert sanitize_string("test{value") == "testvalue"

        # Test that closing curly brace is removed
        assert sanitize_string("test}value") == "testvalue"

        # Test that both braces are removed
        assert sanitize_string("test{value}") == "testvalue"

    def test_dangerous_chars_removed(self):
        """Test that all dangerous shell metacharacters are removed."""
        # Test each dangerous character individually
        assert sanitize_string("test;value") == "testvalue"
        assert sanitize_string("test|value") == "testvalue"
        assert sanitize_string("test&value") == "testvalue"
        assert sanitize_string("test`value") == "testvalue"
        assert sanitize_string("test$value") == "testvalue"
        assert sanitize_string("test(value") == "testvalue"
        assert sanitize_string("test)value") == "testvalue"
        assert sanitize_string("test<value") == "testvalue"
        assert sanitize_string("test>value") == "testvalue"
        assert sanitize_string("test\\value") == "testvalue"

    def test_combined_dangerous_chars(self):
        """Test that multiple dangerous characters are all removed."""
        # Test combination of dangerous characters
        assert sanitize_string(";|&`$()<>{}\\") == ""
        assert sanitize_string("cmd; ls | cat & echo `test` ${var} (test) <redir> {braces}\\escape") == "cmd ls cat echo test var test redir bracesescape"

    def test_safe_chars_preserved(self):
        """Test that safe characters are preserved."""
        # Quotes should be preserved
        assert sanitize_string('test "value"') == 'test "value"'
        assert sanitize_string("test 'value'") == "test 'value'"

        # Brackets should be preserved
        assert sanitize_string("test [value]") == "test [value]"

        # Percentage should be preserved
        assert sanitize_string("test 100%") == "test 100%"

        # Alphanumeric and common punctuation should be preserved
        assert sanitize_string("Test-123_456.") == "Test-123_456."

    def test_regex_pattern_no_range_interpretation(self):
        """
        Test that the regex pattern doesn't interpret }{ as a range.

        This is the core security issue: in the character class [{dangerous_chars}],
        having } next to { could be interpreted as a range. The pattern should be
        written so that - is either escaped or placed at the beginning/end of the
        character class to prevent misinterpretation.
        """
        # Test various edge cases with curly braces
        assert sanitize_string("{") == ""
        assert sanitize_string("}") == ""
        assert sanitize_string("}{") == ""
        assert sanitize_string("a{b}c") == "abc"

        # Test with other characters that might be in ranges
        assert sanitize_string("a-z") == "a-z"  # This should NOT be treated as a range pattern
        assert sanitize_string("test{a-z}value") == "testa-zvalue"
