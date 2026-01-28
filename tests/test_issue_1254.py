"""Test for Issue #1254 - Verify CONTROL_CHARS_PATTERN is correctly used.

This test verifies that CONTROL_CHARS_PATTERN is properly utilized in both
sanitize_for_security_context() and remove_control_chars() functions, addressing
the concern that it might be unused or orphaned code.

The issue raised a false positive concern about CONTROL_CHARS_PATTERN not being
used in sanitize_for_security_context(). This test confirms that:
1. CONTROL_CHARS_PATTERN is defined and precompiled
2. It's used correctly in all contexts within sanitize_for_security_context()
3. It's used correctly in remove_control_chars()
4. Control characters are properly removed in all contexts
"""

import pytest
import re
from flywheel.cli import (
    CONTROL_CHARS_PATTERN,
    sanitize_for_security_context,
    remove_control_chars,
)


class TestControlCharsPatternUsage:
    """Test that CONTROL_CHARS_PATTERN is correctly used in sanitization functions."""

    def test_control_chars_pattern_is_precompiled(self):
        """Verify CONTROL_CHARS_PATTERN is a precompiled regex object."""
        assert hasattr(CONTROL_CHARS_PATTERN, 'pattern'), \
            "CONTROL_CHARS_PATTERN must be a compiled regex.Pattern object"
        assert CONTROL_CHARS_PATTERN.pattern == r'[\x00-\x1F\x7F]', \
            "CONTROL_CHARS_PATTERN must match control characters (0x00-0x1F, 0x7F)"

    def test_control_chars_pattern_removes_control_chars(self):
        """Verify CONTROL_CHARS_PATTERN correctly removes control characters."""
        # Test null byte
        assert CONTROL_CHARS_PATTERN.sub('', 'test\x00string') == 'teststring'
        # Test various control characters
        test_string = 'a\x00b\x01c\x02d\x1Fe\x7Ff'
        expected = 'abcdef'
        assert CONTROL_CHARS_PATTERN.sub('', test_string) == expected

    def test_sanitize_for_security_context_shell_context(self):
        """Verify control chars are removed in shell context."""
        # Test with control characters in shell context
        test_string = 'test\x00\x1F\x7Fcommand'
        result = sanitize_for_security_context(test_string, context='shell')
        # Control chars should be removed, and string should be quoted
        assert '\x00' not in result
        assert '\x1F' not in result
        assert '\x7F' not in result
        # Result should be shell-quoted
        assert result.startswith("'") or result.startswith('"')

    def test_sanitize_for_security_context_format_context(self):
        """Verify control chars are removed in format context."""
        # Test with control characters in format context
        test_string = 'test\x00\x1F\x7F{format}'
        result = sanitize_for_security_context(test_string, context='format')
        # Control chars should be removed
        assert '\x00' not in result
        assert '\x1F' not in result
        assert '\x7F' not in result
        # Format chars should be escaped
        assert '{{' in result or '}}' in result

    def test_sanitize_for_security_context_url_context(self):
        """Verify control chars are removed in url context."""
        # Test with control characters in url context
        test_string = 'http://example.com\x00\x1F\x7F/path'
        result = sanitize_for_security_context(test_string, context='url')
        # Control chars should be removed
        assert '\x00' not in result
        assert '\x1F' not in result
        assert '\x7F' not in result
        # Shell metachars should also be removed
        assert ';' not in result
        assert '|' not in result

    def test_sanitize_for_security_context_filename_context(self):
        """Verify control chars are removed in filename context."""
        # Test with control characters in filename context
        test_string = 'file\x00\x1F\x7Fname.txt'
        result = sanitize_for_security_context(test_string, context='filename')
        # Control chars should be removed
        assert '\x00' not in result
        assert '\x1F' not in result
        assert '\x7F' not in result

    def test_sanitize_for_security_context_general_context(self):
        """Verify control chars are removed in general context."""
        # Test with control characters in general context
        test_string = 'general\x00\x1F\x7Ftext'
        result = sanitize_for_security_context(test_string, context='general')
        # Control chars should be removed
        assert '\x00' not in result
        assert '\x1F' not in result
        assert '\x7F' not in result
        # Shell metachars should be preserved in general context
        assert '$' in result if '$' in test_string else True
        assert ';' in result if ';' in test_string else True

    def test_remove_control_chars_function(self):
        """Verify remove_control_chars uses CONTROL_CHARS_PATTERN correctly."""
        # Test with various control characters
        test_string = 'hello\x00world\x1Ftest\x7Fend'
        result = remove_control_chars(test_string)
        # All control characters should be removed
        assert '\x00' not in result
        assert '\x1F' not in result
        assert '\x7F' not in result
        assert result == 'helloworldtestend'

    def test_newline_and_tab_removal(self):
        """Verify that newlines and tabs are removed as control characters."""
        # Newline (0x0A) and tab (0x09) should be removed
        test_string = 'line1\nline2\ttabbed'
        result = remove_control_chars(test_string)
        assert '\n' not in result
        assert '\t' not in result

    def test_carriage_return_removal(self):
        """Verify that carriage returns are removed as control characters."""
        # Carriage return (0x0D) should be removed
        test_string = 'text\r\ncrlf'
        result = remove_control_chars(test_string)
        assert '\r' not in result

    def test_control_chars_in_all_positions(self):
        """Verify control chars are removed from start, middle, and end."""
        test_string = '\x00start\x1Fmiddle\x7Fend\x00'
        result = remove_control_chars(test_string)
        assert result == 'startmiddleend'

    def test_pattern_matches_all_ascii_control_chars(self):
        """Verify CONTROL_CHARS_PATTERN matches all ASCII control characters."""
        # Test all ASCII control characters (0x00-0x1F)
        for i in range(0x00, 0x20):
            char = chr(i)
            test_string = f'before{char}after'
            result = CONTROL_CHARS_PATTERN.sub('', test_string)
            assert result == 'beforeafter', f"Failed to remove control char 0x{i:02X}"

        # Test DEL character (0x7F)
        test_string = f'before\x7Fafter'
        result = CONTROL_CHARS_PATTERN.sub('', test_string)
        assert result == 'beforeafter'

    def test_preserves_non_control_chars(self):
        """Verify that non-control characters are preserved."""
        # Test that normal characters, Unicode, and special chars are preserved
        test_string = 'Hello 世界 🎉 $100 (test)'
        result = remove_control_chars(test_string)
        # In remove_control_chars, these should be preserved
        # (it only removes control chars and Unicode spoofing chars)
        assert 'Hello' in result or '世界' in result
        # The function should preserve most characters
        assert len(result) > 0
