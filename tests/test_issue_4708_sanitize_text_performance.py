"""Regression tests for Issue #4708: _sanitize_text uses multiple string.replace() calls.

This test file ensures that _sanitize_text has acceptable performance on large inputs.
The current implementation uses multiple string.replace() calls causing O(n*k) string copies.

Acceptance criteria:
- Performance on 1MB string should be under 200ms (current is ~80ms, acceptable)
- All existing tests pass
- No regression in correctness
"""

from __future__ import annotations

import time

import pytest

from flywheel.formatter import _sanitize_text


class TestSanitizeTextPerformance:
    """Test that _sanitize_text performs acceptably on large inputs."""

    @pytest.mark.performance
    def test_sanitize_text_1mb_string_performance(self) -> None:
        """_sanitize_text on 1MB string should complete under 200ms.

        This test measures performance improvement from single-pass implementation
        vs the old multi-replace approach.
        """
        # Build a 1MB string with mix of normal chars, control chars, and backslashes
        chunk = "Hello\\World\x01Test\x7fMore\x80End\n\r\t"
        large_text = chunk * 50000  # Creates ~1.4MB string

        # Verify we have a meaningful test size
        assert len(large_text) >= 1_000_000, f"Test string too small: {len(large_text)}"

        # Time the sanitization
        start = time.perf_counter()
        result = _sanitize_text(large_text)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Acceptance criteria: under 200ms
        assert elapsed_ms < 200, (
            f"_sanitize_text took {elapsed_ms:.1f}ms on 1MB string, exceeds 200ms threshold"
        )

        # Verify correctness: no control chars in result
        assert "\x01" not in result
        assert "\x7f" not in result
        assert "\x80" not in result
        assert "\n" not in result
        assert "\r" not in result
        assert "\t" not in result

        # Verify escaped versions are present
        assert "\\x01" in result
        assert "\\x7f" in result
        assert "\\x80" in result

    @pytest.mark.performance
    def test_sanitize_text_100kb_string_many_backslashes(self) -> None:
        """Test performance with string containing many backslashes.

        Backslashes require escaping, so strings with many backslashes
        stress the single-pass implementation.
        """
        # Build a string with many backslashes
        chunk = "\\path\\to\\file\\" * 100
        large_text = chunk * 10  # ~100KB with many backslashes

        start = time.perf_counter()
        result = _sanitize_text(large_text)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should be fast even with many backslashes
        assert elapsed_ms < 50, f"_sanitize_text took {elapsed_ms:.1f}ms on 100KB with backslashes"

        # Verify correctness: all backslashes should be doubled
        assert "\\\\" in result

    @pytest.mark.performance
    def test_sanitize_text_100kb_string_many_control_chars(self) -> None:
        """Test performance with string containing many control characters.

        Control characters require escaping to \\xNN format.
        """
        # Build a string with many control characters
        control_chars = "".join(chr(i) for i in range(0x01, 0x20) if chr(i) not in "\n\r\t")
        control_chars += chr(0x7F)  # DEL
        control_chars += "".join(chr(i) for i in range(0x80, 0x9F))  # C1 controls

        # Repeat to create larger test
        chunk = (control_chars + "text") * 100
        large_text = chunk * 10

        start = time.perf_counter()
        result = _sanitize_text(large_text)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should be fast even with many control chars
        assert elapsed_ms < 100, (
            f"_sanitize_text took {elapsed_ms:.1f}ms on string with many control chars"
        )

        # Verify all control chars are escaped
        for i in list(range(0x01, 0x20)) + [0x7F] + list(range(0x80, 0x9F)):
            if chr(i) in "\n\r\t":
                continue
            assert chr(i) not in result, f"Control char 0x{i:02x} not escaped"
