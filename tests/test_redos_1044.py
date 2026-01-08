"""Test ReDoS protection in sanitize_for_security_context (Issue #1044)."""
import time
import pytest
from flywheel.cli import sanitize_for_security_context


class TestReDoSProtection:
    """Test ReDoS (Regular Expression Denial of Service) protection."""

    def test_no_redos_with_nested_braces(self):
        """Test that nested braces don't cause ReDoS."""
        # Create a string with many nested braces that could cause catastrophic backtracking
        # This pattern is designed to potentially trigger exponential backtracking
        # in poorly designed regex patterns
        malicious = "{{" * 1000 + "test" + "}}" * 1000

        # Add shell metacharacters
        malicious = malicious + "$$;;&&||"

        start = time.time()
        result = sanitize_for_security_context(malicious, context="shell")
        elapsed = time.time() - start

        # Should complete in under 1 second even with malicious input
        assert elapsed < 1.0, f"Function took {elapsed:.2f}s, potential ReDoS vulnerability"

        # All dangerous characters should be removed in shell context
        assert "{" not in result
        assert "}" not in result
        assert "$" not in result
        assert ";" not in result
        assert "&" not in result
        assert "|" not in result

    def test_no_redos_with_percent_signs(self):
        """Test that many percent signs don't cause ReDoS."""
        # Create a string with many percent signs that could cause issues
        # in regex patterns containing %
        malicious = "%" * 10000 + "test"

        start = time.time()
        result = sanitize_for_security_context(malicious, context="shell")
        elapsed = time.time() - start

        # Should complete quickly
        assert elapsed < 1.0, f"Function took {elapsed:.2f}s, potential ReDoS vulnerability"

        # Percent signs should be removed in shell context
        assert "%" not in result
        assert result == "test"

    def test_no_redos_with_backslashes(self):
        """Test that many backslashes don't cause ReDoS."""
        # Create a string with many backslashes
        # Backslashes in regex character classes can cause issues
        malicious = "\\" * 10000 + "test"

        start = time.time()
        result = sanitize_for_security_context(malicious, context="shell")
        elapsed = time.time() - start

        # Should complete quickly
        assert elapsed < 1.0, f"Function took {elapsed:.2f}s, potential ReDoS vulnerability"

        # Backslashes should be removed in shell context
        assert "\\" not in result

    def test_no_redos_with_mixed_metachars(self):
        """Test that mixed shell metacharacters don't cause ReDoS."""
        # Create a string with alternating shell metacharacters
        # This could cause backtracking in some regex engines
        malicious = (";$%{}" * 5000)

        start = time.time()
        result = sanitize_for_security_context(malicious, context="shell")
        elapsed = time.time() - start

        # Should complete quickly
        assert elapsed < 1.0, f"Function took {elapsed:.2f}s, potential ReDoS vulnerability"

        # All shell metacharacters should be removed
        assert ";" not in result
        assert "$" not in result
        assert "%" not in result
        assert "{" not in result
        assert "}" not in result

    def test_max_length_enforced_before_processing(self):
        """Test that max_length is enforced before any regex processing."""
        # Create a string longer than max_length with potential ReDoS patterns
        malicious = "{{" * 100000 + "test"

        # Use default max_length of 100000
        start = time.time()
        result = sanitize_for_security_context(malicious, context="shell", max_length=100000)
        elapsed = time.time() - start

        # Should complete quickly because length is checked first
        assert elapsed < 1.0, f"Function took {elapsed:.2f}s, max_length not enforced early enough"

        # Result should be truncated
        assert len(result) <= 100000

    def test_general_context_preserves_metachars(self):
        """Test that general context preserves shell metacharacters."""
        test_string = "Cost: $100 (discount) & special; offer | 50% off"

        # In general context, shell metachars should be preserved
        result = sanitize_for_security_context(test_string, context="general")

        # These should be preserved in general context
        assert "$" in result
        assert "(" in result
        assert ")" in result
        assert "&" in result
        assert ";" in result
        assert "|" in result
        assert "%" in result

    def test_shell_context_removes_metachars(self):
        """Test that shell context removes shell metacharacters."""
        test_string = "Cost: $100 (discount) & special; offer | 50% off {test}"

        # In shell context, shell metachars should be removed
        result = sanitize_for_security_context(test_string, context="shell")

        # These should be removed in shell context
        assert "$" not in result
        assert "(" not in result
        assert ")" not in result
        assert "&" not in result
        assert ";" not in result
        assert "|" not in result
        assert "%" not in result
        assert "{" not in result
        assert "}" not in result
        assert "\\" not in result
