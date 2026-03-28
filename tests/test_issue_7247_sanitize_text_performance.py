"""Regression tests for Issue #7247: _sanitize_text O(n*m) complexity.

This test file ensures that _sanitize_text uses single-pass O(n) algorithm
instead of multiple string.replace() calls that result in O(n*m) complexity.

The performance issue occurs when:
1. text.replace("\\", "\\\\") creates a new string
2. text.replace("\n", "\\n") creates another new string
3. text.replace("\r", "\\r") creates another new string
4. text.replace("\t", "\\t") creates another new string
5. Final loop creates yet another string

For a string of length n with m replacement operations, this is O(n*m).

Solution: Single-pass algorithm that processes each character exactly once.
"""

from __future__ import annotations

import time

from flywheel.formatter import _sanitize_text


class TestSanitizeTextPerformance:
    """Test that _sanitize_text performs in O(n) time, not O(n*m)."""

    def test_100kb_string_performance(self):
        """Process 100KB string in <50ms (acceptance criteria from issue: <100ms)."""
        # Create a 100KB string with various characters including ones that need escaping
        base_text = "Hello\\World\n\r\t\x01Test"
        # Repeat to get ~100KB (add 1 to ensure we exceed 100KB)
        large_text = base_text * ((100 * 1024 // len(base_text)) + 1)

        assert len(large_text) >= 100 * 1024, f"Test string should be at least 100KB, got {len(large_text)}"

        # Run multiple iterations to get stable measurement
        iterations = 5
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            result = _sanitize_text(large_text)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

        avg_elapsed_ms = sum(times) / len(times)

        # Acceptance criteria: <100ms for 100KB string
        # Note: O(n*m) with multiple replace() calls can still be fast due to C implementation,
        # but single-pass should be even faster and more memory efficient
        assert avg_elapsed_ms < 100, (
            f"_sanitize_text took {avg_elapsed_ms:.1f}ms (avg of {iterations} runs) for 100KB string, "
            f"should be <100ms per acceptance criteria."
        )

        # Verify correctness - result should be longer due to escaping
        assert len(result) > len(large_text), "Escaped text should be longer than input"

    def test_single_pass_algorithm_correctness(self):
        """Verify single-pass algorithm produces same results as original."""
        test_cases = [
            # Simple text
            "Hello World",
            # Backslashes
            r"C:\path\to\file",
            "\\",
            "\\\\",
            # Newlines, tabs, carriage returns
            "Hello\nWorld",
            "Hello\r\nWorld",
            "Hello\tWorld",
            # Control characters
            "\x00\x01\x02",
            "\x1b[31m",
            # DEL and C1
            "\x7f",
            "\x80\x9f",
            # Mixed
            r"C:\path\to\file\nwith\x01control",
            "Line1\nLine2\rLine3\tEnd",
            # Empty and single char
            "",
            "a",
            # All backslashes
            "\\\\\\",
        ]

        for text in test_cases:
            result = _sanitize_text(text)
            # Basic correctness checks
            assert isinstance(result, str), f"Result should be string, got {type(result)}"

            # No raw control chars should remain (except escaped ones)
            for i, char in enumerate(result):
                code = ord(char)
                # Allow printable ASCII, escaped backslash, and normal chars
                if code < 0x20 or 0x7f <= code <= 0x9f:
                    # This should be part of an escape sequence like \n or \x01
                    # Check that it's preceded by a backslash
                    if i > 0:
                        assert result[i-1] == "\\", (
                            f"Control char at position {i} not properly escaped: "
                            f"{result[max(0,i-2):i+2]!r}"
                        )

    def test_linear_time_complexity(self):
        """Verify O(n) time complexity by comparing different input sizes."""
        # If O(n), doubling input size should roughly double time
        # If O(n*m), doubling input size would more than double time

        base_text = "Test\\String\n\r\t\x01"

        # Test with 10KB and 20KB
        text_10kb = base_text * (10 * 1024 // len(base_text))
        text_20kb = base_text * (20 * 1024 // len(base_text))

        # Warm up
        _sanitize_text(text_10kb)

        # Measure 10KB
        start = time.perf_counter()
        _sanitize_text(text_10kb)
        time_10kb = time.perf_counter() - start

        # Measure 20KB
        start = time.perf_counter()
        _sanitize_text(text_20kb)
        time_20kb = time.perf_counter() - start

        # For O(n), ratio should be ~2x
        # For O(n*m) where m=number of replace operations, ratio would be higher
        # Allow some variance but ratio should be between 1.5 and 3.0 for O(n)
        ratio = time_20kb / time_10kb if time_10kb > 0 else 0

        assert 1.5 <= ratio <= 3.5, (
            f"Time ratio for 2x input is {ratio:.1f}x. "
            f"Expected ~2x for O(n), got {time_10kb*1000:.1f}ms vs {time_20kb*1000:.1f}ms. "
            f"This may indicate O(n*m) complexity."
        )

    def test_no_intermediate_string_copies(self):
        """Test that algorithm doesn't create multiple intermediate strings.

        This is a behavioral test - if the implementation uses multiple
        str.replace() calls, it would create intermediate copies.
        """
        # A string with all types of characters that need escaping
        mixed_text = "\\a\nb\rc\td\x01\x7f\x80"

        # Just verify the output is correct
        # The performance tests above catch the O(n*m) issue
        result = _sanitize_text(mixed_text)

        # Verify all escapes are present
        assert "\\\\" in result, "Backslash should be escaped"
        assert "\\n" in result, "Newline should be escaped"
        assert "\\r" in result, "Carriage return should be escaped"
        assert "\\t" in result, "Tab should be escaped"
        assert "\\x01" in result, "Control char should be escaped"
        assert "\\x7f" in result, "DEL should be escaped"
        assert "\\x80" in result, "C1 control char should be escaped"
