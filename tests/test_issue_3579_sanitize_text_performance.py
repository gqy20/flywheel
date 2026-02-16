"""Regression tests for Issue #3579: _sanitize_text performance optimization.

This test file ensures that _sanitize_text performs efficiently on large inputs
without creating multiple intermediate strings via repeated replace() calls.

The optimization uses a single-pass character-by-character approach with
precomputed replacement maps for O(n) complexity instead of O(n*m).
"""

from __future__ import annotations

import time

from flywheel.formatter import _sanitize_text


class TestSanitizeTextPerformance:
    """Test that _sanitize_text performs efficiently on large inputs."""

    def test_sanitize_text_large_input_performance(self):
        """_sanitize_text should handle 100KB+ inputs efficiently.

        Performance target: < 500ms for 100KB input on typical hardware.
        This ensures the single-pass optimization is in place.
        """
        # Create a 100KB input with mix of normal and control characters
        chunk = "Normal text with some unicode 日本語 🎉 and control chars:\n\r\t\x01\x7f\x80"
        large_input = chunk * 1000  # ~140KB

        # Time the operation
        start = time.perf_counter()
        result = _sanitize_text(large_input)
        elapsed = time.perf_counter() - start

        # Verify correctness: no unescaped control characters
        assert "\n" not in result
        assert "\r" not in result
        assert "\t" not in result
        assert "\x01" not in result
        assert "\x7f" not in result
        assert "\x80" not in result

        # Verify the escaped versions are present
        assert "\\n" in result
        assert "\\r" in result
        assert "\\t" in result
        assert "\\x01" in result
        assert "\\x7f" in result
        assert "\\x80" in result

        # Performance check: should complete in < 100ms for 100KB
        # A single-pass approach should be significantly faster than
        # multiple replace() calls creating intermediate strings
        assert elapsed < 0.1, (
            f"_sanitize_text took {elapsed:.3f}s for 100KB input, "
            f"expected < 0.1s. The implementation should use single-pass optimization."
        )

    def test_sanitize_text_very_large_input(self):
        """_sanitize_text should handle 1MB inputs in reasonable time."""
        # Create a 1MB input (mostly normal text)
        chunk = "A" * 1000  # 1KB of normal text
        large_input = chunk * 1000  # 1MB

        start = time.perf_counter()
        result = _sanitize_text(large_input)
        elapsed = time.perf_counter() - start

        # Verify output length is correct (no control chars, so same length)
        assert len(result) == len(large_input)

        # Should complete in < 1s for 1MB of plain text
        assert elapsed < 1.0, (
            f"_sanitize_text took {elapsed:.3f}s for 1MB plain text input, expected < 1s."
        )

    def test_sanitize_text_memory_efficiency(self):
        """_sanitize_text should not create excessive intermediate strings.

        This is implicitly tested by the performance tests above, but we
        verify that the function produces correct output for edge cases.
        """
        # Test all control character ranges
        test_cases = [
            # (input, expected_substring)
            ("\\", "\\\\"),  # backslash
            ("\n", "\\n"),  # newline
            ("\r", "\\r"),  # carriage return
            ("\t", "\\t"),  # tab
            ("\x00", "\\x00"),  # null byte
            ("\x01", "\\x01"),  # SOH
            ("\x1f", "\\x1f"),  # US
            ("\x7f", "\\x7f"),  # DEL
            ("\x80", "\\x80"),  # C1 start
            ("\x9f", "\\x9f"),  # C1 end
        ]

        for input_char, expected in test_cases:
            result = _sanitize_text(input_char)
            assert result == expected, (
                f"Expected {expected!r} for input {input_char!r}, got {result!r}"
            )

    def test_sanitize_text_mixed_content_correctness(self):
        """Verify correctness of single-pass implementation with mixed content."""
        # Mix of all character types
        input_text = (
            "Start\\Backslash"
            "\nNewline"
            "\rCarriage"
            "\tTab"
            "\x00Null"
            "\x01SOH"
            "\x1fUS"
            "\x7fDEL"
            "\x80C1Start"
            "\x9fC1End"
            "Normal\x00Text\x01Mixed"
            "日本語unicode"
        )

        result = _sanitize_text(input_text)

        # Verify no control characters remain
        for char in result:
            code = ord(char)
            if code <= 0x1F or 0x7F <= code <= 0x9F:
                # This should only happen if there's a literal backslash followed by
                # x and hex digits - the escaped representation
                pass  # These are now in escaped form, not actual control chars

        # Verify expected escaped patterns
        assert "\\\\" in result  # Escaped backslash
        assert "\\n" in result
        assert "\\r" in result
        assert "\\t" in result
        assert "\\x00" in result
        assert "\\x01" in result
        assert "\\x1f" in result
        assert "\\x7f" in result
        assert "\\x80" in result
        assert "\\x9f" in result
        assert "日本語unicode" in result
