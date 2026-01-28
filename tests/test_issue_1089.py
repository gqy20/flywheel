"""Test for Issue #1089 - Verify consistent handling of curly braces and backslashes.

Issue #1089 highlights the importance of using the correct sanitization function
for the appropriate context. This test verifies that:

1. 'general' context preserves curly braces, backslashes, and percent signs
2. 'shell', 'url', and 'filename' contexts remove these characters to prevent injection
3. The security implications are properly documented

The key insight is that remove_control_chars() is for display-only data storage
and should NOT be used when strings will be used in format strings or other
security-sensitive contexts. Instead, sanitize_for_security_context() must be used
with the appropriate context parameter.
"""

import pytest

from flywheel.cli import sanitize_for_security_context, remove_control_chars


class TestIssue1089:
    """Test Issue #1089 - Inconsistent handling of curly braces and backslashes."""

    def test_general_context_preserves_curly_braces(self):
        """General context should preserve curly braces for display purposes."""
        input_str = "Use {format} strings in Python"
        result = sanitize_for_security_context(input_str, context="general")
        assert result == input_str, "General context should preserve curly braces"

    def test_general_context_preserves_backslashes(self):
        """General context should preserve backslashes for display purposes."""
        input_str = "Path: C:\\Users\\Documents"
        result = sanitize_for_security_context(input_str, context="general")
        assert result == input_str, "General context should preserve backslashes"

    def test_general_context_preserves_percent_signs(self):
        """General context should preserve percent signs for display purposes."""
        input_str = "Progress: 50% complete"
        result = sanitize_for_security_context(input_str, context="general")
        assert result == input_str, "General context should preserve percent signs"

    def test_general_context_preserves_shell_metachars(self):
        """General context should preserve shell metacharacters for display."""
        input_str = "Cost: $100 (discount) & more"
        result = sanitize_for_security_context(input_str, context="general")
        assert result == input_str, "General context should preserve shell metachars"

    def test_shell_context_removes_curly_braces(self):
        """Shell context should remove curly braces to prevent injection."""
        input_str = "Use {format} strings"
        result = sanitize_for_security_context(input_str, context="shell")
        assert "{" not in result and "}" not in result, "Shell context should remove curly braces"
        assert result == "Use format strings"

    def test_shell_context_removes_backslashes(self):
        """Shell context should remove backslashes to prevent injection."""
        input_str = "Path: C:\\Users\\Documents"
        result = sanitize_for_security_context(input_str, context="shell")
        assert "\\" not in result, "Shell context should remove backslashes"
        assert result == "Path: C:UsersDocuments"

    def test_shell_context_removes_percent_signs(self):
        """Shell context should remove percent signs to prevent injection."""
        input_str = "Progress: 50% complete"
        result = sanitize_for_security_context(input_str, context="shell")
        assert "%" not in result, "Shell context should remove percent signs"
        assert result == "Progress: 50 complete"

    def test_shell_context_removes_shell_metachars(self):
        """Shell context should remove shell metacharacters to prevent injection."""
        input_str = "Cost: $100 (discount) & more"
        result = sanitize_for_security_context(input_str, context="shell")
        assert "$" not in result and "(" not in result and ")" not in result and "&" not in result
        assert result == "Cost: 100 discount  more"

    def test_filename_context_removes_curly_braces(self):
        """Filename context should remove curly braces to prevent path traversal."""
        input_str = "file{name}.txt"
        result = sanitize_for_security_context(input_str, context="filename")
        assert "{" not in result and "}" not in result
        assert result == "filename.txt"

    def test_url_context_removes_curly_braces(self):
        """URL context should remove curly braces to prevent URL injection."""
        input_str = "http://example.com/{path}"
        result = sanitize_for_security_context(input_str, context="url")
        assert "{" not in result and "}" not in result
        assert result == "http://example.com/path"

    def test_remove_control_chars_preserves_all_special_chars(self):
        """remove_control_chars should preserve all special characters as it's for display only.

        WARNING: This function is for data normalization/display only and does NOT
        provide security protection. For security-sensitive contexts where strings
        will be used in format strings, shell commands, URLs, or filenames, use
        sanitize_for_security_context() with the appropriate context parameter.
        """
        input_str = "Use {format} with $100 \\path% complete"
        result = remove_control_chars(input_str)
        assert "{" in result and "}" in result
        assert "$" in result
        assert "\\" in result
        assert "%" in result
        assert result == input_str

    def test_security_context_documentation_warning(self):
        """Test that demonstrates why security context must be used for format strings.

        This test documents the security vulnerability: if 'general' context strings
        are used in format strings, they remain vulnerable to injection attacks.

        Example vulnerable code:
            # DANGEROUS: Using general context in format string
            user_input = sanitize_for_security_context("{malicious}", context="general")
            log_message = f"User entered: {user_input}"  # VULNERABLE to format injection

        Example safe code:
            # SAFE: Using shell context for format strings
            user_input = sanitize_for_security_context("{malicious}", context="shell")
            log_message = "User entered: %s" % user_input  # SAFE

        Even safer: Use safe_log() function which handles this automatically.
        """
        # General context preserves dangerous characters
        general_str = sanitize_for_security_context("{malicious}", context="general")
        assert "{" in general_str and "}" in general_str

        # Security context removes them
        secure_str = sanitize_for_security_context("{malicious}", context="shell")
        assert "{" not in secure_str and "}" not in secure_str

        # This demonstrates that for any dynamic input used in formatting/logic,
        # sanitize_for_security_context must be used with appropriate context
