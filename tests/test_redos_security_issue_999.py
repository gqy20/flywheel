"""Test cases for Issue #999 - ReDoS protection in SHELL_METACHARS_SECURE_PATTERN.

This test module verifies that the sanitize_for_security_context() function
properly protects against ReDoS (Regular Expression Denial of Service) attacks
when processing strings containing malicious patterns with curly braces {} and
percent signs %.

Issue #999: Potential ReDoS risk in SHELL_METACHARS_SECURE_PATTERN which
contains {} and % characters that could cause catastrophic backtracking when
processing maliciously constructed long strings.

Security Fix: Ensure that max_length parameter is strictly enforced BEFORE any
regex processing to prevent potential ReDoS attacks. The length check should be
at the very beginning of the function, before any processing including Unicode
normalization.
"""

import pytest
import time

from flywheel.cli import sanitize_for_security_context


class TestReDoSProtectionIssue999:
    """Test ReDoS protection in sanitize_for_security_context()."""

    def test_max_length_is_enforced_immediately(self):
        """Verify that max_length is enforced before any processing.

        This test ensures that the length limit is applied at the very start
        of the function, before Unicode normalization and any regex processing.
        This is the most secure approach to prevent ReDoS attacks.

        The fix ensures that even if malicious input is provided, the length
        is checked and truncated BEFORE any expensive operations.
        """
        # Create a string that's longer than the default max_length
        # This string contains many {} and % characters which are in
        # SHELL_METACHARS_SECURE_PATTERN
        malicious_input = "a" * 200000  # Way over the 100000 default limit

        # Process with default max_length (100000)
        result = sanitize_for_security_context(malicious_input, context="shell")

        # Result should be truncated to max_length
        assert len(result) <= 100000, \
            f"Result length {len(result)} exceeds max_length 100000"
        # Original string should remain unchanged (strings are immutable)
        assert len(malicious_input) == 200000

    def test_performance_with_malicious_pattern(self):
        """Verify processing completes quickly even with malicious patterns.

        This test creates a string with many {} and % characters that could
        potentially cause catastrophic backtracking. The function should
        complete quickly (within 1 second) because the length limit is
        enforced before any regex processing.
        """
        # Create a string with many potential ReDoS triggers
        # The pattern includes {} and % which are in SHELL_METACHARS_SECURE_PATTERN
        malicious_input = "{}%{}%{}%{}%" * 25000  # 200000 characters

        start_time = time.time()
        result = sanitize_for_security_context(
            malicious_input,
            context="shell",
            max_length=100000
        )
        elapsed_time = time.time() - start_time

        # Should complete within 1 second even with malicious pattern
        assert elapsed_time < 1.0, \
            f"Processing took {elapsed_time:.2f}s, potential ReDoS vulnerability"
        # Result should be truncated
        assert len(result) <= 100000, \
            f"Result length {len(result)} exceeds max_length 100000"

    def test_custom_max_length_is_respected(self):
        """Verify custom max_length parameter is properly enforced."""
        # Create a string longer than custom limit
        input_string = "test{}%string" * 10000  # 150000 characters

        # Test with smaller custom limit
        custom_limit = 50000
        result = sanitize_for_security_context(
            input_string,
            context="shell",
            max_length=custom_limit
        )

        assert len(result) <= custom_limit, \
            f"Result length {len(result)} exceeds custom max_length {custom_limit}"

    def test_shell_context_removes_curly_braces_and_percent(self):
        """Verify that shell context removes {} and % characters."""
        # Test that curly braces and percent signs are removed in shell context
        test_input = "Test{with}braces%and%percent"
        result = sanitize_for_security_context(test_input, context="shell")

        assert "{" not in result
        assert "}" not in result
        assert "%" not in result
        assert "Test" in result
        assert "with" in result
        assert "braces" in result
        assert "and" in result
        assert "percent" in result

    def test_general_context_preserves_curly_braces_and_percent(self):
        """Verify that general context preserves {} and % characters."""
        # Test that general context preserves these characters
        test_input = "Progress: 50% and {format} string"
        result = sanitize_for_security_context(test_input, context="general")

        # In general context, only shell metachars are removed
        # Curly braces and percent should be preserved
        assert "%" in result
        assert "{" in result
        assert "}" in result

    def test_extreme_length_restriction(self):
        """Verify that extremely small max_length is handled correctly."""
        # Create a long string
        long_input = "a{}%b" * 10000

        # Set very small max_length
        result = sanitize_for_security_context(
            long_input,
            context="shell",
            max_length=10
        )

        assert len(result) <= 10

    def test_empty_string_handling(self):
        """Verify empty string is handled correctly."""
        result = sanitize_for_security_context("", context="shell")
        assert result == ""

    def test_none_input_handling(self):
        """Verify None input is handled correctly."""
        result = sanitize_for_security_context(None, context="shell")
        assert result == ""

    def test_length_limit_works_with_unicode(self):
        """Verify length limit works correctly with Unicode characters."""
        # Create a string with Unicode characters
        unicode_input = "测试{}%字符串" * 10000

        result = sanitize_for_security_context(
            unicode_input,
            context="shell",
            max_length=50000
        )

        assert len(result) <= 50000
