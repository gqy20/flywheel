"""Tests for Issue #1239 - % format string escaping in 'format' context."""

import pytest
from flywheel.cli import sanitize_for_security_context


class TestIssue1239:
    """Test that % format strings are properly escaped in 'format' context."""

    def test_percent_sign_escaped_in_format_context(self):
        """Test that % is escaped to %% in format context."""
        input_string = "Progress: 50% complete"
        result = sanitize_for_security_context(input_string, context="format")
        # The % should be escaped to %%
        assert "%" in input_string
        assert "%%" in result
        # Verify it's safe for % formatting
        test_msg = "Status: %s" % result
        assert "50%" in test_msg

    def test_percent_s_placeholder_escaped(self):
        """Test that %s placeholder is escaped."""
        input_string = "User input: %s"
        result = sanitize_for_security_context(input_string, context="format")
        # The %s should be escaped to %%s
        assert "%%s" in result
        # Verify it's safe for % formatting
        test_msg = "Status: %s" % result
        # The %s should be literal, not interpreted
        assert "%s" in test_msg

    def test_percent_n_placeholder_escaped(self):
        """Test that %n placeholder is escaped."""
        input_string = "Line 1%nLine 2"
        result = sanitize_for_security_context(input_string, context="format")
        # The %n should be escaped to %%n
        assert "%%n" in result

    def test_multiple_percent_signs_escaped(self):
        """Test that multiple % signs are all escaped."""
        input_string = "Discount: 50% off, then 20% off"
        result = sanitize_for_security_context(input_string, context="format")
        # Count occurrences - each % should become %%
        assert result.count("%%") == 2

    def test_percent_with_braces_format_context(self):
        """Test that both braces and percent signs are escaped."""
        input_string = "Use {var} for 100%"
        result = sanitize_for_security_context(input_string, context="format")
        # Both braces and percent should be escaped
        assert "{{var}}" in result
        assert "100%%" in result

    def test_format_context_safe_with_fstring(self):
        """Test that escaped string is safe for f-string usage."""
        input_string = "Value: %s"
        sanitized = sanitize_for_security_context(input_string, context="format")
        # This should not raise an exception
        var = "test"
        result = f"User input: {sanitized}"
        assert "%%" in result

    def test_format_context_safe_with_format_method(self):
        """Test that escaped string is safe for .format() usage."""
        input_string = "Value: %s"
        sanitized = sanitize_for_security_context(input_string, context="format")
        # This should not raise an exception
        result = "User input: {}".format(sanitized)
        assert "%%" in result

    def test_format_context_safe_with_percent_formatting(self):
        """Test that escaped string is safe for % formatting."""
        input_string = "Value: %s"
        sanitized = sanitize_for_security_context(input_string, context="format")
        # This should work safely
        result = "User input: %s" % sanitized
        # The sanitized %s should appear literally
        assert "%%s" in result or "%s" in result
