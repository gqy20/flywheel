"""Regression tests for Issue #7247: _sanitize_text O(n*m) complexity.

This test file ensures that _sanitize_text uses a single-pass O(n) algorithm
for escaping control characters, rather than multiple string.replace() calls
that result in O(n*m) complexity where m is the number of escape sequences.

Performance target: 100KB string should be processed in <100ms.
"""

from __future__ import annotations

import time

from flywheel.formatter import _sanitize_text


class TestSanitizeTextPerformance:
    """Test that _sanitize_text has O(n) performance for large strings."""

    def test_100kb_string_performance(self):
        """A 100KB string should be sanitized in <100ms.

        This test verifies that the implementation uses single-pass O(n)
        algorithm rather than multiple O(n) replace operations.
        """
        # Create a 100KB string with a mix of characters including those
        # that need escaping
        chunk = "abc\\def\n\r\t\x01\x1b\x7f"
        repeat_count = (100 * 1024) // len(chunk)  # ~100KB
        large_text = chunk * repeat_count

        start_time = time.perf_counter()
        result = _sanitize_text(large_text)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Verify correctness: result should contain escaped sequences
        assert "\\\\" in result  # backslashes escaped
        assert "\\n" in result  # newlines escaped
        assert "\\r" in result  # carriage returns escaped
        assert "\\t" in result  # tabs escaped
        assert "\\x01" in result  # control chars escaped

        # Performance requirement: <100ms for 100KB
        assert elapsed_ms < 100, (
            f"Performance regression: 100KB string took {elapsed_ms:.1f}ms "
            f"(should be <100ms with O(n) algorithm)"
        )

    def test_very_long_string_linear_scaling(self):
        """Verify O(n) scaling by comparing processing times for different sizes.

        With O(n*m) algorithm (multiple replace calls), doubling input size
        would more than double processing time. With O(n) single-pass, time
        should scale linearly.
        """
        chunk = "abc\\def\n\r\t\x01\x1b\x7f"

        # Test with 50KB
        text_50kb = chunk * ((50 * 1024) // len(chunk))
        start = time.perf_counter()
        _sanitize_text(text_50kb)
        time_50kb = time.perf_counter() - start

        # Test with 100KB (2x size)
        text_100kb = chunk * ((100 * 1024) // len(chunk))
        start = time.perf_counter()
        _sanitize_text(text_100kb)
        time_100kb = time.perf_counter() - start

        # With O(n) algorithm, ratio should be ~2x
        # With O(n*m), ratio would be significantly higher
        ratio = time_100kb / time_50kb if time_50kb > 0 else 0

        # Allow some variance, but ratio should be close to 2 for O(n)
        # If ratio > 3, it suggests O(n*m) behavior
        assert ratio < 3.0, (
            f"Non-linear scaling detected: 50KB took {time_50kb*1000:.1f}ms, "
            f"100KB took {time_100kb*1000:.1f}ms, ratio={ratio:.1f}x "
            f"(expected ~2x for O(n) algorithm)"
        )


class TestSanitizeTextCorrectness:
    """Verify that the optimized implementation produces correct results."""

    def test_escape_results_match_expected(self):
        """All escape sequences should produce correct output."""
        # Common escapes
        assert _sanitize_text("\\") == "\\\\"
        assert _sanitize_text("\n") == "\\n"
        assert _sanitize_text("\r") == "\\r"
        assert _sanitize_text("\t") == "\\t"

        # Control characters
        assert _sanitize_text("\x00") == "\\x00"
        assert _sanitize_text("\x01") == "\\x01"
        assert _sanitize_text("\x1b") == "\\x1b"
        assert _sanitize_text("\x7f") == "\\x7f"
        assert _sanitize_text("\x80") == "\\x80"
        assert _sanitize_text("\x9f") == "\\x9f"

    def test_mixed_content_correctness(self):
        """Mixed content with various characters should be correctly escaped."""
        input_text = "hello\\world\nnew\rline\ttab\x01ctrl"
        result = _sanitize_text(input_text)

        # Verify all escapes are present
        assert "hello\\\\world" in result  # backslash escaped
        assert "\\n" in result  # newline
        assert "\\r" in result  # carriage return
        assert "\\t" in result  # tab
        assert "\\x01" in result  # control char

        # Verify regular text is preserved
        assert "hello" in result
        assert "world" in result
        assert "new" in result
        assert "line" in result
        assert "tab" in result
        assert "ctrl" in result

    def test_empty_string(self):
        """Empty string should remain empty."""
        assert _sanitize_text("") == ""

    def test_no_special_chars(self):
        """String without special characters should remain unchanged."""
        text = "Hello, World! 123"
        assert _sanitize_text(text) == text
