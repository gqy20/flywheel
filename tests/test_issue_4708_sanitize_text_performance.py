"""Regression tests for Issue #4708: _sanitize_text single-pass optimization.

This test file ensures that the performance optimization (single-pass implementation)
maintains correctness while improving efficiency.

The original implementation made multiple string copies:
1. text.replace("\\", "\\\\") - first copy
2. Three more replace() calls - 3 more copies
3. Character iteration with list building - another pass

The optimized version should process the string in a single pass.
"""

from __future__ import annotations

import time

from flywheel.formatter import _sanitize_text


class TestSanitizeTextPerformance:
    """Performance and correctness tests for _sanitize_text optimization."""

    def test_performance_on_large_input(self):
        """Benchmark _sanitize_text with 1M character string.

        Performance target: under 1000ms for ~1.5M chars in CI environments.
        The issue notes ~80ms baseline; CI may be slower.
        The key verification is correctness; timing is informational.
        """
        # Create a ~1.5MB string with mixed content
        # Include normal chars, control chars, backslashes, unicode
        chunk = "Normal text\\with\x01control\x7fchars\n\t日本語€✓\x80\x9f"
        large_text = chunk * 50000  # ~1.5M chars

        start = time.perf_counter()
        result = _sanitize_text(large_text)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Verify correctness: no unescaped control chars
        assert "\x01" not in result
        assert "\x7f" not in result
        assert "\n" not in result
        assert "\t" not in result
        assert "\x80" not in result
        assert "\x9f" not in result

        # Verify unicode passes through
        assert "日本語" in result
        assert "€" in result
        assert "✓" in result

        # Performance assertion: generous threshold for CI variability
        # Issue target is ~80ms baseline; allow up to 1000ms for slow CI
        assert elapsed_ms < 1000, f"Performance regression: {elapsed_ms:.1f}ms > 1000ms threshold"

    def test_correctness_basic_escapes(self):
        """Verify basic escape sequences are still correct after optimization."""
        # Newline
        assert _sanitize_text("\n") == r"\n"
        # Carriage return
        assert _sanitize_text("\r") == r"\r"
        # Tab
        assert _sanitize_text("\t") == r"\t"
        # Backslash
        assert _sanitize_text("\\") == r"\\"

    def test_correctness_control_chars(self):
        """Verify control character escaping is correct."""
        # Null byte
        assert _sanitize_text("\x00") == r"\x00"
        # SOH
        assert _sanitize_text("\x01") == r"\x01"
        # ESC
        assert _sanitize_text("\x1b") == r"\x1b"
        # DEL
        assert _sanitize_text("\x7f") == r"\x7f"

    def test_correctness_c1_controls(self):
        """Verify C1 control characters are correctly escaped."""
        assert _sanitize_text("\x80") == r"\x80"
        assert _sanitize_text("\x9f") == r"\x9f"

    def test_correctness_backslash_collision_prevention(self):
        """Verify backslash escape prevents collision with control chars."""
        # Actual control char vs literal backslash text must be different
        actual_control = _sanitize_text("\x01")
        literal_text = _sanitize_text(r"\x01")
        assert actual_control != literal_text

        # Specific expected outputs
        assert actual_control == r"\x01"  # Control char becomes \x01
        assert literal_text == r"\\x01"  # Literal \x01 becomes \\x01

    def test_correctness_mixed_content(self):
        """Verify mixed content is correctly processed."""
        input_text = "Hello\nWorld\\\x01Test\r\n\tEnd\x7f"
        result = _sanitize_text(input_text)

        # No unescaped control chars
        assert "\n" not in result
        assert "\r" not in result
        assert "\t" not in result
        assert "\x01" not in result
        assert "\x7f" not in result

        # Expected escapes present
        assert r"\n" in result
        assert r"\r" in result
        assert r"\t" in result
        assert r"\x01" in result
        assert r"\x7f" in result

    def test_correctness_unicode_passthrough(self):
        """Verify unicode characters pass through unchanged."""
        assert _sanitize_text("日本語") == "日本語"
        assert _sanitize_text("café") == "café"
        assert _sanitize_text("🎉") == "🎉"
        assert _sanitize_text("€") == "€"
        assert _sanitize_text("你好") == "你好"

    def test_empty_string(self):
        """Empty string should remain empty."""
        assert _sanitize_text("") == ""

    def test_all_normal_chars_passthrough(self):
        """String with only normal characters should be unchanged."""
        normal = "The quick brown fox jumps over the lazy dog 0123456789"
        assert _sanitize_text(normal) == normal
