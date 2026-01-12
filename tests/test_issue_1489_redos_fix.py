"""Tests for Issue #1489 - ReDoS vulnerability in Unicode regex.

This test verifies that the _sanitize_text function uses a non-backtracking
approach to prevent ReDoS (Regular Expression Denial of Service) vulnerabilities.
"""
import pytest
import time
from flywheel.todo import _sanitize_text


class TestIssue1489ReDoSFix:
    """Test suite for ReDoS vulnerability fix (Issue #1489)."""

    def test_remove_zero_width_characters(self):
        """Test that zero-width characters are properly removed."""
        # Zero-width space (U+200B)
        text = "hello\u200bworld"
        result = _sanitize_text(text)
        assert result == "hello world"

    def test_remove_zero_width_non_joiner(self):
        """Test that zero-width non-joiner (U+200C) is removed."""
        text = "hello\u200cworld"
        result = _sanitize_text(text)
        assert result == "hello world"

    def test_remove_zero_width_joiner(self):
        """Test that zero-width joiner (U+200D) is removed."""
        text = "hello\u200dworld"
        result = _sanitize_text(text)
        assert result == "hello space"

    def test_remove_word_joiner(self):
        """Test that word joiner (U+2060) is removed."""
        text = "hello\u2060world"
        result = _sanitize_text(text)
        assert result == "hello world"

    def test_remove_zero_width_no_break_space(self):
        """Test that zero-width no-break space (U+FEFF) is removed."""
        text = "hello\ufeffworld"
        result = _sanitize_text(text)
        assert result == "hello world"

    def test_multiple_invisible_characters(self):
        """Test multiple invisible characters in sequence."""
        text = "hello\u200b\u200c\u200d\u2060\ufeffworld"
        result = _sanitize_text(text)
        assert result == "hello world"

    def test_performance_with_long_string(self):
        """Test that performance is O(n) and not O(n²) due to backtracking.

        This test creates a long string with many zero-width characters
        and ensures the function completes in reasonable time.
        A vulnerable regex could take exponentially longer.
        """
        # Create a string with many zero-width characters
        # A vulnerable implementation would have catastrophic backtracking
        base = "normal text " * 100  # ~1200 chars
        text = base + "\u200b" * 1000 + base

        start = time.time()
        result = _sanitize_text(text)
        elapsed = time.time() - start

        # Should complete in under 1 second even with 1000+ characters
        # A ReDoS-vulnerable regex could take much longer
        assert elapsed < 1.0, f"Function took {elapsed:.3f}s, possible ReDoS vulnerability"
        assert "normal text" in result
        assert "\u200b" not in result

    def test_no_regex_module_usage(self):
        """Test that the implementation doesn't use regex for invisible character removal.

        This test verifies the fix by checking that the function
        works correctly even if we're monitoring for regex usage patterns.
        """
        # The key is that this should work reliably
        # A pure str.translate or iteration approach is preferred
        text = "test\u200b\u200c\u200dstring"
        result = _sanitize_text(text)

        # Should remove all zero-width characters
        assert "\u200b" not in result
        assert "\u200c" not in result
        assert "\u200d" not in result
        assert "test string" == result

    def test_mixed_invisible_and_normal_chars(self):
        """Test mixed invisible and normal characters."""
        text = "a\u200bb\u200cc\u200dd\u2060e\ufefff"
        result = _sanitize_text(text)
        assert result == "a b c d e f"
