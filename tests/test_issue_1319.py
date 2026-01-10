"""Test for Issue #1319 - Format string injection in general context.

Issue #1319 highlights that the 'general' context preserves format string characters
({, }, %, \) which makes it UNSAFE for use in format strings. This test verifies
the fix that removes these dangerous characters from the general context.

The fix: The 'general' context now removes format string characters ({, }, %, \)
to prevent format string injection attacks, making it safer even if developers
accidentally use the output in format strings.
"""

import pytest

from flywheel.cli import sanitize_for_security_context


class TestIssue1319:
    """Test Issue #1319 - Format string injection prevention in general context."""

    def test_general_context_removes_braces(self):
        """General context should remove curly braces to prevent format string injection."""
        # Single braces should be removed
        assert sanitize_for_security_context("Use {format} strings", context="general") == "Use format strings"
        assert sanitize_for_security_context("item}", context="general") == "item"
        assert sanitize_for_security_context("{key}", context="general") == "key"

    def test_general_context_removes_percent(self):
        """General context should remove percent signs to prevent % formatting injection."""
        assert sanitize_for_security_context("Progress: 50%", context="general") == "Progress: 50"
        assert sanitize_for_security_context("100% complete", context="general") == "100 complete"
        assert sanitize_for_security_context("Discount: 20%", context="general") == "Discount: 20"

    def test_general_context_removes_backslash(self):
        """General context should remove backslashes to prevent escape sequence issues."""
        assert sanitize_for_security_context("C:\\Users\\path", context="general") == "C:Userspath"
        assert sanitize_for_security_context("\\path\\to\\file", context="general") == "pathtofile")

    def test_general_context_safe_in_fstring(self):
        """Verify that general context strings are safe in f-strings after fix."""
        user_input = sanitize_for_security_context("{malicious_code}", context="general")
        # After fix, braces are removed
        assert user_input == "malicious_code"
        # Safe to use in f-string
        result = f"User entered: {user_input}"
        assert result == "User entered: malicious_code"

    def test_general_context_safe_in_percent_formatting(self):
        """Verify that general context strings are safe in % formatting after fix."""
        user_input = sanitize_for_security_context("100%s complete", context="general")
        # After fix, percent signs are removed
        assert user_input == "100s complete"
        # Safe to use in % formatting
        message = "Progress: %s" % user_input
        assert message == "Progress: 100s complete"

    def test_general_context_neutralizes_malicious_input(self):
        """Test that malicious input with format string characters is neutralized."""
        # Various malicious payloads that should be neutralized
        test_cases = [
            ("{__import__('os').system('rm -rf /')}", "__import__('os').system('rm -rf /')"),
            ("%s%s%s%s", "ssss"),
            ("\\x41\\x42\\x43", "x41x42x43"),
            ("{key}", "key"),
        ]

        for payload, expected in test_cases:
            result = sanitize_for_security_context(payload, context="general")
            assert result == expected, f"Failed for payload: {payload}"

    def test_general_context_vs_format_context(self):
        """Compare general context with format context after fix."""
        input_str = "Use {var} for 100% on C:\\path"

        # Format context escapes dangerous characters (safe for format strings)
        format_result = sanitize_for_security_context(input_str, context="format")
        assert format_result == "Use {{var}} for 100%% on C:\\\\path"

        # General context removes dangerous characters (also safe)
        general_result = sanitize_for_security_context(input_str, context="general")
        assert general_result == "Use var for 100 on C:path"

        # Both should be safe, just different approaches
        # Format context: escapes for literal display in format strings
        # General context: removes to prevent any injection risk

    def test_general_context_preserves_safe_content(self):
        """General context should preserve safe characters while removing dangerous ones."""
        # Normal text should be unchanged
        assert sanitize_for_security_context("Hello World", context="general") == "Hello World"

        # Alphanumeric and most punctuation preserved
        assert sanitize_for_security_context("Cost: $100 (discount)", context="general") == "Cost: $100 (discount)"

        # Shell metachars should be preserved in general context (Issue #1024)
        assert sanitize_for_security_context("Command & more", context="general") == "Command & more"

        # But format string chars should be removed (Issue #1319)
        assert sanitize_for_security_context("Use {var} for 100%", context="general") == "Use var for 100"
