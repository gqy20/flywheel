"""Tests for Issue #780 - Shell injection protection robustness.

This test verifies that the sanitize_string function uses a robust approach
to prevent shell injection. The issue suggests that using multiple sequential
regex passes could be fragile and recommends a single combined approach.

Current implementation: Two separate regex passes
- Line 129: Removes shell metacharacters (;|&`$()<>{}\)
- Line 133: Removes control characters (\x00-\x1F\x7F)

Recommended improvement: Single combined regex pass for robustness.
"""

import pytest
import re
from flywheel.cli import sanitize_string


class TestRobustSanitization:
    """Test suite for robust sanitization approach."""

    def test_shell_metacharacters_removed(self):
        """Test that all shell metacharacters are removed."""
        dangerous_chars = [';', '|', '&', '`', '$', '(', ')', '<', '>', '{', '}']

        for char in dangerous_chars:
            malicious = f"todo{char}evil"
            result = sanitize_string(malicious)
            assert char not in result, f"Dangerous char '{char}' should be removed"

    def test_control_characters_removed(self):
        """Test that all control characters are removed."""
        # Test key control characters
        control_chars = ['\n', '\r', '\t', '\x00', '\x0A', '\x0D', '\x1F', '\x7F']

        for char in control_chars:
            malicious = f"todo{char}evil"
            result = sanitize_string(malicious)
            assert char not in result, f"Control char '{repr(char)}' should be removed"

    def test_combined_attack_newline_with_semicolon(self):
        """Test the specific attack scenario: newline + shell metacharacters.

        This addresses the core concern in Issue #780 about potential bypass
        through combining control characters with shell metacharacters.
        """
        # Attack: newline followed by semicolon command injection
        malicious = "todo\ncmd; rm -rf /"
        result = sanitize_string(malicious)

        # Both newline AND semicolon must be removed
        assert '\n' not in result, "Newline must be removed"
        assert ';' not in result, "Semicolon must be removed"
        assert '\r' not in result, "Carriage return must be removed"

    def test_combined_attack_control_chars_with_metachars(self):
        """Test various combinations of control characters and metacharacters."""
        attack_vectors = [
            "todo\n;evil",
            "todo\r|evil",
            "todo\t&evil",
            "todo\x00`evil",
            "todo; \nevil",
            "todo| \revil",
        ]

        for attack in attack_vectors:
            result = sanitize_string(attack)
            # Should have no control characters
            assert '\n' not in result
            assert '\r' not in result
            assert '\t' not in result
            # Should have no shell metacharacters
            assert ';' not in result
            assert '|' not in result
            assert '&' not in result
            assert '`' not in result

    def test_all_ascii_control_chars_removed(self):
        """Test that ALL ASCII control characters (0x00-0x1F, 0x7F) are removed."""
        # Test every control character in the range
        for i in list(range(0x00, 0x20)) + [0x7F]:
            malicious = f"todo{chr(i)}evil"
            result = sanitize_string(malicious)
            assert chr(i) not in result, f"Control char 0x{i:02X} should be removed"

    def test_sanitization_is_idempotent(self):
        """Test that sanitization is idempotent - running it twice gives same result.

        This property ensures no characters can slip through due to order dependencies.
        """
        malicious = "todo; cmd|evil&bad`rm${}\n\r\t\x00"
        result1 = sanitize_string(malicious)
        result2 = sanitize_string(result1)

        assert result1 == result2, "Sanitization should be idempotent"

    def test_backslashes_removed(self):
        """Test that backslashes are removed (Issue #736, #769)."""
        # Backslashes can act as escape characters in shell contexts
        malicious = "todo\\evil"
        result = sanitize_string(malicious)
        assert '\\' not in result, "Backslashes must be removed to prevent shell injection"

    def test_complex_combined_attack(self):
        """Test a complex attack with multiple character types."""
        # Attack combining all dangerous character types
        malicious = "todo\n; cmd|evil&bad`rm${}\\\t\x00"
        result = sanitize_string(malicious)

        # Verify all dangerous characters are removed
        dangerous = [';', '|', '&', '`', '$', '(', ')', '<', '>', '{', '}', '\\']
        for char in dangerous:
            assert char not in result, f"Character '{char}' should be removed"

        # Verify control characters are removed
        assert '\n' not in result
        assert '\r' not in result
        assert '\t' not in result
        assert '\x00' not in result

    def test_legitimate_content_preserved(self):
        """Test that legitimate content is preserved."""
        legitimate_cases = [
            "Normal todo item",
            "Todo with 'quotes'",
            'Todo with "double quotes"',
            "Todo with - hyphens",
            "Todo with [brackets]",
            "Todo with % percent",
            "UUID: 550e8400-e29b-41d4-a716-446655440000",
            "Date: 2024-01-15",
            "Phone: 1-800-555-0123",
        ]

        for text in legitimate_cases:
            result = sanitize_string(text)
            # These should be preserved (or only minimally changed)
            assert len(result) > 0, f"Legitimate text should not be empty: '{text}'"

    def test_empty_and_none_inputs(self):
        """Test edge cases: empty string and None."""
        assert sanitize_string("") == ""
        assert sanitize_string(None) == ""
