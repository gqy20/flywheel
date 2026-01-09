"""Tests for Issue #1169 - Format string character escaping in 'format' context."""

import pytest
from flywheel.cli import sanitize_for_security_context


class TestFormatContextEscaping:
    """Test that format context properly escapes format string characters."""

    def test_escape_curly_braces(self):
        """Test that curly braces are properly escaped."""
        # Test single braces
        assert sanitize_for_security_context("{", context="format") == "{{"
        assert sanitize_for_security_context("}", context="format") == "}}"

        # Test braces in text
        assert sanitize_for_security_context("Use {var}", context="format") == "Use {{var}}"
        assert sanitize_for_security_context("Replace {x} with {y}", context="format") == "Replace {{x}} with {{y}}"

    def test_escape_percent_sign(self):
        """Test that percent signs are properly escaped."""
        # Test single percent
        assert sanitize_for_security_context("%", context="format") == "%%"

        # Test percent in text
        assert sanitize_for_security_context("50%", context="format") == "50%%"
        assert sanitize_for_security_context("Progress: 100%", context="format") == "Progress: 100%%"
        assert sanitize_for_security_context("20% off", context="format") == "20%% off"

    def test_escape_backslash(self):
        """Test that backslashes are properly escaped."""
        # Test single backslash
        assert sanitize_for_security_context("\\", context="format") == "\\\\"

        # Test backslash in text
        assert sanitize_for_security_context("C:\\Users", context="format") == "C:\\\\Users"
        assert sanitize_for_security_context("\\n\\t\\r", context="format") == "\\\\n\\\\t\\\\r"

    def test_escape_combined(self):
        """Test that all format characters are escaped together."""
        # Test complex string with all special characters
        input_str = "Use {var} for 100% complete\\n"
        expected = "Use {{var}} for 100%% complete\\\\n"
        assert sanitize_for_security_context(input_str, context="format") == expected

    def test_format_context_preserves_other_content(self):
        """Test that format context preserves other safe content."""
        # Test that normal text is preserved
        assert sanitize_for_security_context("Hello World", context="format") == "Hello World"
        assert sanitize_for_security_context("Test-123", context="format") == "Test-123"
        assert sanitize_for_security_context("email@example.com", context="format") == "email@example.com"

    def test_format_context_with_nfkc_normalization(self):
        """Test that format context applies NFKC normalization before escaping."""
        # Test fullwidth characters are normalized before format escaping
        # Fullwidth braces should be normalized to ASCII then escaped
        assert sanitize_for_security_context("｛test｝", context="format") == "{{test}}"

        # Fullwidth percent should be normalized then escaped
        result = sanitize_for_security_context("５０％", context="format")
        assert "%%" in result  # Should contain escaped percent

    def test_format_context_vs_general_context(self):
        """Test that format context behaves differently from general context."""
        test_str = "Use {var} for 50%"

        # Format context should escape
        format_result = sanitize_for_security_context(test_str, context="format")
        assert "{{" in format_result
        assert "%%" in format_result

        # General context should preserve
        general_result = sanitize_for_security_context(test_str, context="general")
        assert "{var}" in general_result
        assert "50%" in general_result

    def test_format_context_empty_string(self):
        """Test that format context handles empty strings."""
        assert sanitize_for_security_context("", context="format") == ""

    def test_format_context_multiple_escapes(self):
        """Test multiple consecutive format characters."""
        assert sanitize_for_security_context("{{{", context="format") == "{{{{{{"
        assert sanitize_for_security_context("%%%", context="format") == "%%%%%%%%"
        assert sanitize_for_security_context("\\\\\\", context="format") == "\\\\\\\\\\\\"

    def test_format_context_prevents_injection_in_fstring(self):
        """Test that escaped strings are safe in f-strings."""
        # Simulate what happens when using sanitized string in f-string
        user_input = "{malicious_code}"
        sanitized = sanitize_for_security_context(user_input, context="format")

        # In an f-string, {{ becomes literal {
        # So f"User: {sanitized}" would display "User: {malicious_code}"
        # This prevents the injection
        assert sanitized == "{{malicious_code}}"

    def test_format_context_prevents_percent_format_injection(self):
        """Test that escaped strings are safe in % formatting."""
        # Simulate % formatting injection attempt
        user_input = "%s%s%s%s"
        sanitized = sanitize_for_security_context(user_input, context="format")

        # Each % should be doubled
        assert sanitized == "%%s%%s%%s%%s"

        # This would be interpreted as literal "%s%s%s%s" in % formatting
        # Not as format specifiers

    def test_format_context_order_of_operations(self):
        """Test that backslash escaping happens first to avoid double-escaping."""
        # This test verifies the implementation order
        # Backslash must be escaped first to avoid escaping the escape characters
        input_str = "\\n{test}%d"

        # The expected result should have:
        # 1. \ → \\
        # 2. { → {{
        # 3. } → }}
        # 4. % → %%
        result = sanitize_for_security_context(input_str, context="format")
        assert result == "\\\\n{{test}}%%d"
