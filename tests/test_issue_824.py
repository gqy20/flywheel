"""Test for Issue #824 - sanitize_string preserves dangerous characters

This test verifies that sanitize_string currently preserves quotes and percent signs,
which can be dangerous in shell contexts. The fix should clarify that this function
is NOT suitable for shell sanitization and should only be used for basic data cleaning.
"""

import pytest
from flywheel.cli import sanitize_string


class TestIssue824ShellInjectionVulnerability:
    """Test suite for Issue #824 - Shell injection vulnerability in sanitize_string."""

    def test_single_quote_preserved(self):
        """Test that single quotes are preserved (demonstrates vulnerability)."""
        # Input with single quote that could be used for shell injection
        malicious_input = "'; DROP TABLE todos; --"
        result = sanitize_string(malicious_input)
        # Current implementation preserves single quotes - this is the VULNERABILITY
        # After fix, the function should either:
        # 1. Remove quotes, OR
        # 2. Document that it's NOT safe for shell contexts
        assert "'" in result, "Current implementation preserves single quotes (vulnerable)"

    def test_double_quote_preserved(self):
        """Test that double quotes are preserved (demonstrates vulnerability)."""
        malicious_input = '"; rm -rf /; #'
        result = sanitize_string(malicious_input)
        # Current implementation preserves double quotes - this is the VULNERABILITY
        assert '"' in result, "Current implementation preserves double quotes (vulnerable)"

    def test_percent_sign_preserved(self):
        """Test that percent signs are preserved (can be dangerous)."""
        # Percent signs can be dangerous in format strings or certain shell contexts
        malicious_input = "Complete %s and %d tasks"
        result = sanitize_string(malicious_input)
        # Current implementation preserves percent signs
        assert '%' in result, "Current implementation preserves percent signs"

    def test_combined_dangerous_characters(self):
        """Test combination of dangerous characters that could enable injection."""
        # This combines multiple preserved characters that could be exploited
        malicious_input = '''title'; echo "hacked"; #'''
        result = sanitize_string(malicious_input)
        # Verify that dangerous characters are preserved
        assert "'" in result or '"' in result, "Dangerous quotes preserved"

    def test_command_substitution_attempt(self):
        """Test that command substitution patterns are partially handled."""
        # Backticks and $() should be removed (and they are)
        malicious_input = "Hello`whoami`World$(date)"
        result = sanitize_string(malicious_input)
        # These ARE removed - good
        assert '`' not in result
        assert '$' not in result
        # But quotes are NOT removed - bad
        assert "'" in result or '"' in result

    def test_shell_metacharacters_removed(self):
        """Test that basic shell metacharacters are removed (partial protection)."""
        # Some characters ARE removed correctly
        malicious_input = "cmd1; cmd2 | cmd3 & cmd4"
        result = sanitize_string(malicious_input)
        assert ';' not in result, "Semicolons removed"
        assert '|' not in result, "Pipes removed"
        assert '&' not in result, "Ampersands removed"

    def test_function_purpose_misleading(self):
        """Test that demonstrates the function's purpose is misleading.

        The function claims to prevent shell injection but preserves quotes
        which are the PRIMARY mechanism for shell injection. This test
        documents that the function should NOT be used for shell safety.
        """
        # A realistic shell injection attempt using quotes
        malicious_input = """'$(cat /etc/passwd)'"""
        result = sanitize_string(malicious_input)
        # The function preserves the quotes, making this UNSAFE for shell use
        # The $() is removed, but the quotes remain
        assert '"' in result or "'" in result, "Quotes are preserved (not shell-safe)"
