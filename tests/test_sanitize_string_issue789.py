"""Tests for sanitize_string function - Issue #789

This test file verifies that the sanitize_string function properly implements
the documented "single combined regex pass" approach to remove dangerous characters.

Issue #789 states that the code only implements Unicode script filtering but
is missing the regex replacement step to remove specific dangerous characters
like shell metacharacters ({}, \, etc.)

According to the documentation (lines 42-43):
- "Uses a single combined regex pass to remove all dangerous characters atomically"
- "This prevents order-dependency issues and makes the sanitization more robust"
"""

import pytest
from flywheel.cli import sanitize_string


class TestSanitizeStringDangerousChars:
    """Test removal of dangerous characters via regex."""

    def test_remove_semicolon(self):
        """Test that semicolon is removed."""
        assert sanitize_string("hello;world") == "helloworld"

    def test_remove_pipe(self):
        """Test that pipe is removed."""
        assert sanitize_string("hello|world") == "helloworld"

    def test_remove_ampersand(self):
        """Test that ampersand is removed."""
        assert sanitize_string("hello&world") == "helloworld"

    def test_remove_backtick(self):
        """Test that backtick is removed."""
        assert sanitize_string("hello`world") == "helloworld"

    def test_remove_dollar_sign(self):
        """Test that dollar sign is removed."""
        assert sanitize_string("hello$world") == "helloworld"

    def test_remove_parentheses(self):
        """Test that parentheses are removed."""
        assert sanitize_string("hello(world)") == "helloworld"

    def test_remove_angle_brackets(self):
        """Test that angle brackets are removed."""
        assert sanitize_string("hello<world>") == "helloworld"

    def test_remove_curly_braces(self):
        """Test that curly braces are removed."""
        assert sanitize_string("hello{world}") == "helloworld"

    def test_remove_backslash(self):
        """Test that backslash is removed."""
        assert sanitize_string("hello\\world") == "helloworld"

    def test_remove_newline(self):
        """Test that newline is removed."""
        assert sanitize_string("hello\nworld") == "helloworld"

    def test_remove_tab(self):
        """Test that tab is removed."""
        assert sanitize_string("hello\tworld") == "helloworld"

    def test_remove_null_byte(self):
        """Test that null byte is removed."""
        assert sanitize_string("hello\x00world") == "helloworld"

    def test_combined_dangerous_chars(self):
        """Test that multiple dangerous characters are removed in one pass."""
        # Test the documented "single combined regex pass" behavior
        input_str = "test;cmd|exec&run`script$var()(args)<inj>{malic}\\ious\nchars\t"
        expected = "testcmdexectrunscriptvarargsinjmaliciouschars"
        assert sanitize_string(input_str) == expected

    def test_preserve_quotes(self):
        """Test that quotes are preserved (legitimate content)."""
        assert sanitize_string("hello'world'") == "hello'world'"
        assert sanitize_string('hello"world"') == 'hello"world"'

    def test_preserve_percentage(self):
        """Test that percentage is preserved."""
        assert sanitize_string("50% complete") == "50% complete"

    def test_preserve_spaces(self):
        """Test that spaces are preserved (Issue #849)."""
        assert sanitize_string("hello world") == "hello world"
        assert sanitize_string("test value") == "test value"

    def test_preserve_brackets(self):
        """Test that brackets are preserved."""
        assert sanitize_string("array[0]") == "array[0]"

    def test_preserve_hyphen(self):
        """Test that hyphen is preserved."""
        assert sanitize_string("well-known") == "well-known"
        assert sanitize_string("550e8400-e29b-41d4-a716-446655440000") == "550e8400-e29b-41d4-a716-446655440000"

    def test_order_independence(self):
        """Test that sanitization is order-independent (no bypass via character ordering)."""
        # This tests the "single combined regex pass" property
        # If the implementation uses multiple passes, certain character orderings
        # could potentially bypass filters
        dangerous_cases = [
            (";\n", ""),  # semicolon + newline
            ("|\\", ""),  # pipe + backslash
            ("&\t", ""),  # ampersand + tab
            ("`$", ""),   # backtick + dollar
            ("{}\x00", ""),  # braces + null
        ]

        for input_str, expected in dangerous_cases:
            result = sanitize_string(input_str)
            assert result == expected, f"Failed for {repr(input_str)}: got {repr(result)}"


class TestSanitizeStringUnicode:
    """Test Unicode script filtering (Issue #774)."""

    def test_remove_cyrillic(self):
        """Test that Cyrillic characters are removed."""
        # Latin 'a' vs Cyrillic 'а' (visually identical)
        assert sanitize_string("admin") == "admin"
        # Cyrillic 'а' should be removed
        result = sanitize_string("аdmin")  # Cyrillic а
        # Should remove Cyrillic and keep only Latin
        assert result == "dmin"

    def test_remove_greek(self):
        """Test that Greek characters are removed."""
        # Greek epsilon should be removed
        assert sanitize_string("testε") == "test"

    def test_preserve_latin_accented(self):
        """Test that Latin accented characters are preserved."""
        assert sanitize_string("café") == "café"
        assert sanitize_string("naïve") == "naïve"
        assert sanitize_string("über") == "über"


class TestSanitizeStringIntegration:
    """Integration tests combining dangerous chars and Unicode filtering."""

    def test_dangerous_chars_with_cyrillic(self):
        """Test that dangerous chars and non-Latin chars are both removed."""
        # This test verifies that the sanitization handles both types of filtering
        input_str = "test;admin|команда&exec"
        # Should remove: ; | &, Cyrillic команда
        # Result: "testadminexec"
        result = sanitize_string(input_str)
        assert result == "testadminexec"

    def test_comprehensive_sanitization(self):
        """Test comprehensive sanitization with all character types."""
        input_str = "Тест;test|command&exec`run$scr\x00ipt()(args)<{malic}\\ious\n\t"
        # Should remove: Cyrillic Тест, shell metachars, control chars
        # Result: "testcommandexecscriprgsmalicious"
        expected = "testcommandexecscriprgsmalicious"
        assert sanitize_string(input_str) == expected
