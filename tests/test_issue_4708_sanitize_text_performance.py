"""Regression tests for Issue #4708: _sanitize_text performance optimization.

This test file verifies that _sanitize_text uses an efficient single-pass
implementation (O(n)) instead of multiple string.replace() calls (O(n*k)).

The issue was that the old implementation:
1. Called text.replace("\\\\", "\\\\\\\\") - O(n) string copy
2. Called text.replace("\n", "\\n") - O(n) string copy
3. Called text.replace("\r", "\\r") - O(n) string copy
4. Called text.replace("\t", "\\t") - O(n) string copy
5. Then iterated character by character - O(n)

This created 4 intermediate string copies for large inputs.

The optimized implementation uses str.translate() or single-pass iteration
to avoid creating multiple intermediate strings.
"""

from __future__ import annotations

import time

from flywheel.formatter import _sanitize_text


class TestSanitizeTextPerformance:
    """Test that _sanitize_text performs efficiently on large inputs."""

    def test_performance_1mb_string_under_200ms(self):
        """Performance benchmark: 1MB string should be processed under 200ms.

        This test verifies the fix for Issue #4708 - the function should use
        a single-pass approach (O(n)) rather than multiple replace() calls (O(n*k)).

        The acceptance criteria from the issue:
        - Performance on 1MB string should be under 200ms (current ~80ms is acceptable)
        """
        # Create a 1MB string with mix of normal and control characters
        # This simulates realistic input with occasional control chars
        chunk = "Normal text with some tabs\there and newlines\n" * 100
        large_text = chunk * (1024 * 1024 // len(chunk))  # ~1MB

        # Measure performance
        start = time.perf_counter()
        result = _sanitize_text(large_text)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Verify correctness: the result should be different (sanitized)
        assert result != large_text  # Control chars should be escaped

        # Verify performance: should be under 200ms
        assert elapsed_ms < 200, (
            f"_sanitize_text took {elapsed_ms:.1f}ms for 1MB string, "
            f"expected < 200ms. Issue #4708 regression detected."
        )

    def test_performance_string_with_many_control_chars(self):
        """Test performance on string with many control characters.

        This tests the worst case where the character-by-character loop
        is heavily used. The single-pass approach should handle this efficiently.
        """
        # Create a string with many control characters
        # This stresses the control char escaping path
        control_chars = "".join(chr(i) for i in range(32))  # C0 controls
        control_chars += chr(0x7f)  # DEL
        control_chars += "".join(chr(i) for i in range(0x80, 0xa0))  # C1 controls

        # Repeat to create a reasonably sized test
        large_text = (control_chars + "normal text ") * 1000

        start = time.perf_counter()
        result = _sanitize_text(large_text)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should complete in reasonable time
        assert elapsed_ms < 500, (
            f"_sanitize_text took {elapsed_ms:.1f}ms for string with many control chars, "
            f"expected < 500ms. Issue #4708 regression detected."
        )

        # Verify correctness: control chars should be escaped
        assert len(result) > len(large_text)  # Escaped version is longer


class TestSanitizeTextCorrectnessAfterOptimization:
    """Verify correctness is maintained after performance optimization."""

    def test_backslash_escaping_still_works(self):
        """Ensure backslash escaping is preserved after optimization."""
        # From Issue #2097 - backslash must be escaped FIRST
        assert _sanitize_text("\\") == r"\\"
        assert _sanitize_text(r"\n") == r"\\n"
        assert _sanitize_text("\n") == r"\n"

    def test_common_control_chars_still_work(self):
        """Ensure common control char replacements are preserved."""
        assert _sanitize_text("\n") == r"\n"
        assert _sanitize_text("\r") == r"\r"
        assert _sanitize_text("\t") == r"\t"

    def test_other_control_chars_still_work(self):
        """Ensure other control char escaping is preserved."""
        # C0 controls
        assert _sanitize_text("\x00") == r"\x00"
        assert _sanitize_text("\x01") == r"\x01"
        assert _sanitize_text("\x1b") == r"\x1b"

        # DEL
        assert _sanitize_text("\x7f") == r"\x7f"

        # C1 controls
        assert _sanitize_text("\x80") == r"\x80"
        assert _sanitize_text("\x9f") == r"\x9f"

    def test_mixed_content_correctness(self):
        """Test mixed content with backslashes and control chars."""
        # Complex case with backslash + newline + other controls
        result = _sanitize_text("\\\n\t\x01")
        assert result == r"\\\n\t\x01"
