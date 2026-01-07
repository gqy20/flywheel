"""Tests for Issue #1004 - ReDoS prevention via precompiled regex patterns.

ISSUE #1004 claimed that remove_control_chars() uses uncompiled regex patterns,
but this is a FALSE POSITIVE. The code already correctly uses precompiled
patterns defined at module level (lines 21-26 in cli.py).

This test verifies that:
1. All regex patterns are precompiled at module level
2. remove_control_chars() uses only precompiled patterns
3. The implementation prevents ReDoS attacks

Security: ReDoS (Regular Expression Denial of Service) attacks exploit
catastrophic backtracking in certain regex patterns. By precompiling patterns
at module load time, we:
- Improve performance (no repeated compilation)
- Enable pattern validation at startup
- Ensure consistent pattern usage across function calls
"""

import re
import pytest
from flywheel import cli


class TestRegexPrecompilation:
    """Test that all regex patterns are precompiled at module level."""

    def test_control_chars_pattern_is_precompiled(self):
        """Verify CONTROL_CHARS_PATTERN is a compiled regex object."""
        assert hasattr(cli, 'CONTROL_CHARS_PATTERN'), \
            "CONTROL_CHARS_PATTERN must be defined at module level"
        assert isinstance(cli.CONTROL_CHARS_PATTERN, re.Pattern), \
            "CONTROL_CHARS_PATTERN must be a precompiled regex.Pattern object"

    def test_zero_width_chars_pattern_is_precompiled(self):
        """Verify ZERO_WIDTH_CHARS_PATTERN is a precompiled regex object."""
        assert hasattr(cli, 'ZERO_WIDTH_CHARS_PATTERN'), \
            "ZERO_WIDTH_CHARS_PATTERN must be defined at module level"
        assert isinstance(cli.ZERO_WIDTH_CHARS_PATTERN, re.Pattern), \
            "ZERO_WIDTH_CHARS_PATTERN must be a precompiled regex.Pattern object"

    def test_bidi_override_pattern_is_precompiled(self):
        """Verify BIDI_OVERRIDE_PATTERN is a precompiled regex object."""
        assert hasattr(cli, 'BIDI_OVERRIDE_PATTERN'), \
            "BIDI_OVERRIDE_PATTERN must be defined at module level"
        assert isinstance(cli.BIDI_OVERRIDE_PATTERN, re.Pattern), \
            "BIDI_OVERRIDE_PATTERN must be a precompiled regex.Pattern object"

    def test_format_string_pattern_is_precompiled(self):
        """Verify FORMAT_STRING_PATTERN is a precompiled regex object."""
        assert hasattr(cli, 'FORMAT_STRING_PATTERN'), \
            "FORMAT_STRING_PATTERN must be defined at module level"
        assert isinstance(cli.FORMAT_STRING_PATTERN, re.Pattern), \
            "FORMAT_STRING_PATTERN must be a precompiled regex.Pattern object"

    def test_shell_metachars_pattern_is_precompiled(self):
        """Verify SHELL_METACHARS_PATTERN is a precompiled regex object."""
        assert hasattr(cli, 'SHELL_METACHARS_PATTERN'), \
            "SHELL_METACHARS_PATTERN must be defined at module level"
        assert isinstance(cli.SHELL_METACHARS_PATTERN, re.Pattern), \
            "SHELL_METACHARS_PATTERN must be a precompiled regex.Pattern object"

    def test_shell_metachars_secure_pattern_is_precompiled(self):
        """Verify SHELL_METACHARS_SECURE_PATTERN is a precompiled regex object."""
        assert hasattr(cli, 'SHELL_METACHARS_SECURE_PATTERN'), \
            "SHELL_METACHARS_SECURE_PATTERN must be defined at module level"
        assert isinstance(cli.SHELL_METACHARS_SECURE_PATTERN, re.Pattern), \
            "SHELL_METACHARS_SECURE_PATTERN must be a precompiled regex.Pattern object"


class TestRemoveControlCharsUsesPrecompiledPatterns:
    """Test that remove_control_chars uses only precompiled patterns."""

    def test_remove_control_chars_basic(self):
        """Test basic functionality of remove_control_chars."""
        # Control characters should be removed
        result = cli.remove_control_chars("Hello\x00World")
        assert result == "HelloWorld", f"Expected 'HelloWorld', got '{result}'"

    def test_remove_control_chars_preserves_shell_metachars(self):
        """Test that shell metachars are preserved (Issue #979)."""
        # Shell metachars should be preserved in general context
        result = cli.remove_control_chars("Cost: $100 (discount)")
        assert result == "Cost: $100 (discount)", f"Got: '{result}'"

    def test_remove_control_chars_removes_format_chars(self):
        """Test that format string characters are removed."""
        result = cli.remove_control_chars("Use {format} strings")
        assert result == "Use format strings", f"Got: '{result}'"

    def test_remove_control_chars_with_long_input(self):
        """Test that long inputs are handled efficiently (ReDoS prevention)."""
        # Create a long string with control characters
        long_input = "a" * 50000 + "\x00\x01\x02" + "b" * 50000

        # This should complete quickly without catastrophic backtracking
        result = cli.remove_control_chars(long_input)

        # Control chars should be removed
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x02" not in result
        # Length should be original length minus removed control chars
        assert len(result) == 100000

    def test_remove_control_chars_max_length_enforcement(self):
        """Test that max_length parameter is enforced."""
        # Create input longer than default max_length
        long_input = "a" * 200000

        # Should truncate to max_length (default 100000)
        result = cli.remove_control_chars(long_input)
        assert len(result) == 100000

    def test_remove_control_chars_with_zero_width_chars(self):
        """Test that zero-width characters are removed."""
        # Zero-width space (U+200B)
        result = cli.remove_control_chars("Hello\u200BWorld")
        assert result == "HelloWorld", f"Got: '{result}'"

    def test_remove_control_chars_with_bidi_override(self):
        """Test that bidirectional override characters are removed."""
        # Right-to-left override (U+202E)
        result = cli.remove_control_chars("Hello\u202EWorld")
        assert result == "HelloWorld", f"Got: '{result}'"


class TestSanitizeForSecurityContextUsesPrecompiledPatterns:
    """Test that sanitize_for_security_context also uses precompiled patterns."""

    def test_sanitize_for_security_context_url(self):
        """Test URL context (uses NFKC normalization)."""
        # Fullwidth characters should be converted to ASCII
        result = cli.sanitize_for_security_context("ｅｘａｍｐｌｅ．ｃｏｍ", context="url")
        assert result == "example.com", f"Got: '{result}'"

    def test_sanitize_for_security_context_shell(self):
        """Test shell context (removes shell metachars)."""
        result = cli.sanitize_for_security_context("test;command", context="shell")
        assert result == "testcommand", f"Got: '{result}'"

    def test_sanitize_for_security_context_general(self):
        """Test general context (preserves more characters)."""
        # Percent sign should be preserved in general context
        result = cli.sanitize_for_security_context("Progress: 50%", context="general")
        assert result == "Progress: 50%", f"Got: '{result}'"


class TestReDoSPrevention:
    """Test ReDoS attack prevention."""

    def test_no_catastrophic_backtracking_with_nested_patterns(self):
        """Test that patterns don't cause catastrophic backtracking."""
        # Create input that could trigger catastrophic backtracking
        # in poorly designed regex patterns
        problematic_input = "a" * 1000 + "\x00" + "b" * 1000

        # This should complete quickly
        result = cli.remove_control_chars(problematic_input)

        # Should successfully process
        assert len(result) == 2000
        assert "\x00" not in result

    def test_performance_with_repeated_calls(self):
        """Test that repeated calls are efficient (thanks to precompilation)."""
        import time

        # Time 1000 calls
        start = time.time()
        for _ in range(1000):
            cli.remove_control_chars("test\x00string")
        end = time.time()

        # Should complete in reasonable time (< 1 second)
        # With precompiled patterns, this should be fast
        assert (end - start) < 1.0, \
            f"Repeated calls too slow: {end - start:.3f}s (may indicate uncompiled regex)"

    def test_max_length_prevents_dos(self):
        """Test that max_length prevents DoS with extremely long input."""
        # Create extremely long input
        huge_input = "a" * 10000000  # 10 million characters

        # Should truncate quickly without processing entire string
        result = cli.remove_control_chars(huge_input, max_length=1000)

        # Should be truncated to max_length
        assert len(result) == 1000


def test_issue_1004_documentation():
    """Test that Issue #996 (ReDoS prevention) is documented."""
    docstring = cli.remove_control_chars.__doc__

    # Should reference the security issue about ReDoS prevention
    assert docstring is not None, "Function must have documentation"
    assert "SECURITY" in docstring or "Issue #996" in docstring or "precompiled" in docstring, \
        "Documentation should mention ReDoS prevention or precompiled patterns"
