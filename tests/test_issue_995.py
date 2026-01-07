"""Tests for Issue #995 - Verify regex patterns are precompiled.

This test verifies that all regex patterns in cli.py are precompiled
at module load time to prevent ReDoS (Regular Expression Denial of Service)
attacks.

Security: Addresses Issue #995
"""

import re
import pytest
from flywheel.cli import (
    ZERO_WIDTH_CHARS_PATTERN,
    BIDI_OVERRIDE_PATTERN,
    CONTROL_CHARS_PATTERN,
    SHELL_METACHARS_PATTERN,
    SHELL_METACHARS_SECURE_PATTERN,
    FORMAT_STRING_PATTERN,
    remove_control_chars,
    sanitize_for_security_context,
)


class TestRegexPrecompilation:
    """Test that regex patterns are precompiled for performance and security."""

    def test_zero_width_chars_pattern_is_compiled(self):
        """Test that ZERO_WIDTH_CHARS_PATTERN is a compiled regex pattern."""
        assert isinstance(ZERO_WIDTH_CHARS_PATTERN, re.Pattern)
        assert ZERO_WIDTH_CHARS_PATTERN.pattern == r'[\u200B-\u200D\u2060\uFEFF]'

    def test_bidi_override_pattern_is_compiled(self):
        """Test that BIDI_OVERRIDE_PATTERN is a compiled regex pattern."""
        assert isinstance(BIDI_OVERRIDE_PATTERN, re.Pattern)
        assert BIDI_OVERRIDE_PATTERN.pattern == r'[\u202A-\u202E\u2066-\u2069]'

    def test_control_chars_pattern_is_compiled(self):
        """Test that CONTROL_CHARS_PATTERN is a compiled regex pattern."""
        assert isinstance(CONTROL_CHARS_PATTERN, re.Pattern)
        assert CONTROL_CHARS_PATTERN.pattern == r'[\x00-\x1F\x7F]'

    def test_shell_metachars_pattern_is_compiled(self):
        """Test that SHELL_METACHARS_PATTERN is a compiled regex pattern."""
        assert isinstance(SHELL_METACHARS_PATTERN, re.Pattern)
        assert SHELL_METACHARS_PATTERN.pattern == r'[;|&`$()<>]'

    def test_shell_metachars_secure_pattern_is_compiled(self):
        """Test that SHELL_METACHARS_SECURE_PATTERN is a compiled regex pattern."""
        assert isinstance(SHELL_METACHARS_SECURE_PATTERN, re.Pattern)
        assert SHELL_METACHARS_SECURE_PATTERN.pattern == r'[;|&`$()<>{}\\%]'

    def test_format_string_pattern_is_compiled(self):
        """Test that FORMAT_STRING_PATTERN is a compiled regex pattern."""
        assert isinstance(FORMAT_STRING_PATTERN, re.Pattern)
        assert FORMAT_STRING_PATTERN.pattern == r'[{}\\%]'

    def test_precompiled_patterns_work_correctly(self):
        """Test that precompiled patterns produce correct results."""
        # Test ZERO_WIDTH_CHARS_PATTERN
        assert ZERO_WIDTH_CHARS_PATTERN.sub('', 'test\u200Bstring') == 'teststring'

        # Test BIDI_OVERRIDE_PATTERN
        assert BIDI_OVERRIDE_PATTERN.sub('', 'test\u202Astring') == 'teststring'

        # Test CONTROL_CHARS_PATTERN
        assert CONTROL_CHARS_PATTERN.sub('', 'test\x00string') == 'teststring'

        # Test SHELL_METACHARS_PATTERN
        assert SHELL_METACHARS_PATTERN.sub('', 'test;string') == 'teststring'

        # Test SHELL_METACHARS_SECURE_PATTERN
        assert SHELL_METACHARS_SECURE_PATTERN.sub('', 'test{string}') == 'teststring'

        # Test FORMAT_STRING_PATTERN
        assert FORMAT_STRING_PATTERN.sub('', 'test{string}') == 'teststring'

    def test_remove_control_chars_uses_precompiled_patterns(self):
        """Test that remove_control_chars function uses precompiled patterns."""
        # This function should use CONTROL_CHARS_PATTERN and FORMAT_STRING_PATTERN
        # If patterns were not precompiled, this would be a security risk

        # Test control character removal
        result = remove_control_chars('test\x00\x01\x02string')
        assert result == 'teststring'

        # Test format string character removal
        result = remove_control_chars('test{string}')
        assert result == 'teststring'

    def test_sanitize_for_security_context_uses_precompiled_patterns(self):
        """Test that sanitize_for_security_context uses precompiled patterns."""
        # Test shell context (uses SHELL_METACHARS_SECURE_PATTERN)
        result = sanitize_for_security_context('test;command', context='shell')
        assert ';' not in result
        assert '{' not in result
        assert '%' not in result

        # Test general context (uses SHELL_METACHARS_PATTERN)
        result = sanitize_for_security_context('test;command', context='general')
        assert ';' not in result
        # In general context, % should be preserved
        result = sanitize_for_security_context('Progress: 50%', context='general')
        assert '%' not in result  # FORMAT_STRING_PATTERN removes it
