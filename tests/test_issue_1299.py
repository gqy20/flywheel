"""Tests for Issue #1299 - format context escaping logic."""

import pytest
from flywheel.cli import sanitize_for_security_context


class TestFormatContextEscaping:
    """Test that format context properly escapes format string characters."""

    def test_format_context_escapes_curly_braces(self):
        """Test that format context escapes { and } characters."""
        # Test single braces
        assert sanitize_for_security_context("{", context="format") == "{{"
        assert sanitize_for_security_context("}", context="format") == "}}"

        # Test braces in text
        assert sanitize_for_security_context("Use {var}", context="format") == "Use {{var}}"
        assert sanitize_for_security_context("Replace {var} with value", context="format") == "Replace {{var}} with value"

    def test_format_context_escapes_percent_signs(self):
        """Test that format context escapes % characters."""
        # Test single percent
        assert sanitize_for_security_context("%", context="format") == "%%"

        # Test percent in text
        assert sanitize_for_security_context("50%", context="format") == "50%%"
        assert sanitize_for_security_context("Progress: 100%", context="format") == "Progress: 100%%"

    def test_format_context_escapes_backslashes(self):
        """Test that format context escapes \\ characters."""
        # Test single backslash
        assert sanitize_for_security_context("\\", context="format") == "\\\\"

        # Test backslash in text
        assert sanitize_for_security_context("C:\\Users", context="format") == "C:\\\\Users"

    def test_format_context_escapes_combined(self):
        """Test format context with all special characters combined."""
        # From the docstring example
        result = sanitize_for_security_context("Use {var} for 100%", context="format")
        assert result == "Use {{var}} for 100%%"

        # More complex example
        result = sanitize_for_security_context("Path: C:\\Users\\{name}\\file.txt - 50% complete", context="format")
        assert result == "Path: C:\\\\Users\\\\{{name}}\\\\file.txt - 50%% complete"

    def test_format_context_removes_control_chars(self):
        """Test that format context removes control characters before escaping."""
        # Control chars should be removed
        result = sanitize_for_security_context("Hello\x00World", context="format")
        assert result == "HelloWorld"

    def test_general_context_preserves_format_chars(self):
        """Test that general context preserves format string characters."""
        # General context should NOT escape format chars
        assert sanitize_for_security_context("{var}", context="general") == "{var}"
        assert sanitize_for_security_context("50%", context="general") == "50%"
        assert sanitize_for_security_context("C:\\Users", context="general") == "C:\\Users"
