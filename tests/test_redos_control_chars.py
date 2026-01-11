"""Tests for ReDoS vulnerability in control character sanitization (Issue #1414).

This test ensures that the sanitization function handles potentially malicious
input that could cause catastrophic backtracking or performance degradation.
"""

import time
import pytest
from flywheel.todo import _sanitize_text


class TestReDoSControlCharacters:
    """Test cases for ReDoS vulnerability in control character removal."""

    def test_simple_control_chars_removed(self):
        """Basic test: control characters should be removed."""
        # Test basic control characters
        text_with_null = "Hello\x00World"
        result = _sanitize_text(text_with_null)
        assert result == "HelloWorld"

    def test_long_string_performance(self):
        """Test that long strings with control characters are handled efficiently.

        This test ensures the implementation doesn't suffer from ReDoS when
        processing long strings with many control characters.
        """
        # Create a long string with alternating control characters
        # This could trigger catastrophic backtracking in vulnerable regex
        base_text = "a" * 100

        # Build a potentially problematic string with repeated patterns
        # that could cause backtracking
        problematic = base_text * 1000  # 100,000 characters
        problematic += "\x00" * 100

        # Time the operation - should complete quickly (< 0.1 second for this size)
        start = time.time()
        result = _sanitize_text(problematic)
        elapsed = time.time() - start

        # Should complete in reasonable time - strict threshold for ReDoS prevention
        assert elapsed < 0.1, f"Sanitization took {elapsed:.3f}s, possible ReDoS vulnerability"
        # Control characters should be removed
        assert "\x00" not in result

    def test_nested_control_chars(self):
        """Test strings with repeated control character patterns."""
        # Pattern that could cause backtracking in vulnerable implementations
        text = "test" + "\x00\x01\x02" * 100 + "end"
        result = _sanitize_text(text)

        # Control characters should be removed
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x02" not in result
        assert "testend" in result

    def test_all_ascii_control_chars(self):
        """Test all ASCII control characters are removed."""
        # All control characters from the issue
        control_text = (
            "\x00\x01\x02\x03\x04\x05\x06\x07\x08"  # 0-8
            "\x0b\x0c"  # 11-12 (skip \t, \n which are 9-10)
            "\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f"  # 14-31
            "\x7f"  # DEL
        )
        text = "Start" + control_text + "End"
        result = _sanitize_text(text)

        # None of the control characters should remain
        for cc in control_text:
            assert cc not in result, f"Control character {ord(cc):02x} not removed"
        assert result == "StartEnd"
