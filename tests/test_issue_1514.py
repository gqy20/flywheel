"""Test for Issue #1514 - Inconsistent handling of format string characters.

This test verifies that:
1. The 'general' context preserves format string characters ({, }, %, \)
2. The 'format' context escapes format string characters safely
3. FORMAT_STRING_PATTERN is properly utilized (or removed if dead code)
"""

import pytest
from flywheel.cli import sanitize_for_security_context, FORMAT_STRING_PATTERN


class TestFormatStringCharacterHandling:
    """Test format string character handling for Issue #1514."""

    def test_general_context_preserves_format_chars(self):
        """General context should preserve format string characters."""
        # Test with percent sign
        assert sanitize_for_security_context("Progress: 50%", context="general") == "Progress: 50%"
        # Test with curly braces
        assert sanitize_for_security_context("Use {var} for value", context="general") == "Use {var} for value"
        # Test with backslash
        assert sanitize_for_security_context("Path: C:\\Users\\file", context="general") == "Path: C:\\Users\\file"
        # Test with all format chars combined
        assert sanitize_for_security_context("Test {all} % chars \\ test", context="general") == "Test {all} % chars \\ test"

    def test_format_context_escapes_braces(self):
        """Format context should escape curly braces."""
        # Single braces should be doubled
        assert sanitize_for_security_context("Use {var}", context="format") == "Use {{var}}"
        assert sanitize_for_security_context("value}", context="format") == "value}}"

    def test_format_context_escapes_percent(self):
        """Format context should escape percent signs."""
        assert sanitize_for_security_context("50%", context="format") == "50%%"
        assert sanitize_for_security_context("Progress: 100%", context="format") == "Progress: 100%%"

    def test_format_context_escapes_backslash(self):
        """Format context should escape backslashes."""
        assert sanitize_for_security_context("C:\\Users", context="format") == "C:\\\\Users"
        assert sanitize_for_security_context("\\", context="format") == "\\\\"

    def test_format_context_escapes_combined(self):
        """Format context should escape all format string characters."""
        # Test combined format string characters
        result = sanitize_for_security_context("Use {var} for 100% path\\test", context="format")
        assert result == "Use {{var}} for 100%% path\\\\test"

    def test_format_string_pattern_matches_format_chars(self):
        """FORMAT_STRING_PATTERN should match format string characters."""
        # Should match backslash
        assert FORMAT_STRING_PATTERN.search('\\') is not None
        # Should match percent
        assert FORMAT_STRING_PATTERN.search('%') is not None
        # Should match opening brace
        assert FORMAT_STRING_PATTERN.search('{') is not None
        # Should match closing brace
        assert FORMAT_STRING_PATTERN.search('}') is not None
        # Should not match regular characters
        assert FORMAT_STRING_PATTERN.search('abc') is None

    def test_format_string_pattern_in_context(self):
        """Test that format string pattern is used appropriately in different contexts."""
        # General context should preserve all format chars
        test_string = "{val} % path\\test"
        general_result = sanitize_for_security_context(test_string, context="general")
        assert '{' in general_result
        assert '}' in general_result
        assert '%' in general_result
        assert '\\' in general_result

        # Format context should escape all format chars
        format_result = sanitize_for_security_context(test_string, context="format")
        assert '{{' in format_result or '{' not in format_result or format_result.count('{') == 0
        assert '}}' in format_result or '}' not in format_result or format_result.count('}') == 0
        assert '%%' in format_result
        assert '\\\\' in format_result

    def test_url_filename_context_remove_format_chars(self):
        """URL and filename contexts should remove format string characters."""
        # URL context should remove format chars
        url_result = sanitize_for_security_context("file{test}%20name", context="url")
        assert '{' not in url_result
        assert '}' not in url_result
        assert '%' not in url_result

        # Filename context should remove format chars
        file_result = sanitize_for_security_context("file{test}%name", context="filename")
        assert '{' not in file_result
        assert '}' not in file_result
        assert '%' not in file_result
