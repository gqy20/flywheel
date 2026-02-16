"""Regression tests for Issue #3579: _sanitize_text performance optimization.

This test file ensures that _sanitize_text is optimized to use a single-pass
approach instead of creating multiple intermediate strings via repeated replace() calls.
"""

from __future__ import annotations

import time

from flywheel.formatter import _sanitize_text


class TestSanitizeTextPerformance:
    """Test that _sanitize_text is performant on large inputs."""

    def test_sanitize_text_large_input_performance(self):
        """Test that _sanitize_text handles 100KB+ input efficiently.

        The optimized implementation should complete in under 100ms for 100KB input.
        The old implementation with multiple replace() calls would be significantly slower.
        """
        # Create a 100KB input with various characters including control chars
        # Mix of normal text, newlines, tabs, backslashes, and control chars
        chunk = "Normal text\\with\nbackslash\tand\rcontrol\x01\x02\x7f\x80\x9fchars"
        # Repeat to get ~100KB
        large_input = chunk * (100 * 1024 // len(chunk))

        # Measure performance
        start_time = time.perf_counter()
        result = _sanitize_text(large_input)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should complete in under 100ms for 100KB input
        # This is a conservative upper bound; the optimized version should be much faster
        assert elapsed_ms < 100, (
            f"_sanitize_text took {elapsed_ms:.1f}ms for 100KB input, "
            f"expected < 100ms. The implementation may be using inefficient "
            f"multiple replace() calls instead of single-pass processing."
        )

        # Verify correctness - result should not contain actual control chars
        assert "\n" not in result
        assert "\r" not in result
        assert "\t" not in result
        assert "\x01" not in result
        assert "\x7f" not in result
        assert "\x80" not in result
        assert "\x9f" not in result

        # Verify escaped versions are present
        assert "\\n" in result
        assert "\\r" in result
        assert "\\t" in result
        assert "\\\\with" in result  # Backslash should be escaped

    def test_sanitize_text_very_large_input(self):
        """Test that _sanitize_text handles 1MB input efficiently.

        The optimized implementation should complete in under 1 second for 1MB input.
        """
        # Create a 1MB input
        chunk = "Text with \t tabs\nand other\x00control\x7fchars\\backslash"
        large_input = chunk * (1024 * 1024 // len(chunk))

        start_time = time.perf_counter()
        result = _sanitize_text(large_input)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should complete in under 1000ms (1 second) for 1MB input
        assert elapsed_ms < 1000, (
            f"_sanitize_text took {elapsed_ms:.1f}ms for 1MB input, "
            f"expected < 1000ms."
        )

        # Basic correctness check
        assert "\n" not in result
        assert "\t" not in result
        assert "\x00" not in result
        assert "\x7f" not in result
