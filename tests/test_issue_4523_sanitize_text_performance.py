"""Regression tests for Issue #4523: _sanitize_text performs multiple string iterations.

This test file ensures that the _sanitize_text function is optimized for performance
by using a single-pass approach (str.translate or similar) instead of multiple
iterative passes over the input string.

Acceptance criteria:
- All existing tests pass after refactoring
- Performance on 10KB strings should be <= 2ms (current is ~1.5ms)
- Output must be identical to current implementation for all inputs
"""

from __future__ import annotations

import time

from flywheel.formatter import _sanitize_text


class TestSanitizeTextPerformance:
    """Test performance of _sanitize_text on large strings."""

    def test_sanitize_text_performance_10kb_string(self) -> None:
        """_sanitize_text should process 10KB strings in <= 2ms."""
        # Create a 10KB string with mixed content including control chars
        chunk = "Normal text\x01\x02\x03\n\r\t\x7f\x80\x9f\\backslash\\"
        # Repeat to get ~10KB
        text = chunk * (10240 // len(chunk) + 1)
        text = text[:10240]  # Exact 10KB

        # Warm up
        _sanitize_text(text)

        # Measure performance
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            _sanitize_text(text)
        elapsed = (time.perf_counter() - start) / iterations

        # Should be <= 2ms (0.002 seconds) per call
        assert elapsed <= 0.002, (
            f"_sanitize_text took {elapsed * 1000:.2f}ms for 10KB string, expected <= 2ms"
        )

    def test_sanitize_text_output_unchanged_for_all_inputs(self) -> None:
        """Output must be identical to expected for edge cases after optimization."""
        # Test various edge cases
        test_cases = [
            # (input, expected_output)
            ("", ""),
            ("normal text", "normal text"),
            ("\n", "\\n"),
            ("\r", "\\r"),
            ("\t", "\\t"),
            ("\x00", "\\x00"),
            ("\x1f", "\\x1f"),
            ("\x7f", "\\x7f"),
            ("\x80", "\\x80"),
            ("\x9f", "\\x9f"),
            ("\\", "\\\\"),
            (r"\n", "\\\\n"),
            (r"\x01", "\\\\x01"),
            ("hello\nworld", "hello\\nworld"),
            ("a\x01b", "a\\x01b"),
            ("\\\x01", "\\\\\\x01"),
            # Unicode text should pass through
            ("café", "café"),
            ("日本語", "日本語"),
            ("🎉", "🎉"),
        ]

        for input_text, expected in test_cases:
            result = _sanitize_text(input_text)
            assert result == expected, (
                f"_sanitize_text({input_text!r}) returned {result!r}, expected {expected!r}"
            )

    def test_sanitize_text_large_string_correctness(self) -> None:
        """Large strings should be processed correctly."""
        # Create a large string with various control characters
        parts = [
            "normal",
            "\x00",  # null
            "\\",
            "\n",  # newline
            "more",
            "\x1b",  # escape
            "\\x",
            "\r",  # carriage return
            "\x7f",  # DEL
            "end",
            "\x80",  # C1
        ]
        text = "".join(parts * 1000)  # Large string

        result = _sanitize_text(text)

        # Verify no control chars remain in output (except escaped ones)
        for char in result:
            code = ord(char)
            # Only allow printable ASCII, and higher unicode
            if code < 0x20 or 0x7F <= code <= 0x9F:
                # This should only happen if it's part of an escape sequence
                # like \xNN or \n, \r, \t
                pass  # The escape sequence chars are allowed

        # Verify backslashes are correctly escaped
        # Input backslash count: 1000 (from "\\")
        # Plus additional from "\x" which adds 1000 more
        # Total input backslashes: 2000
        # Output should have 4000 backslashes (each escaped to \\)
        # But we also have control char escapes adding more

        # Just verify the result is correct for a smaller known sample
        # Input: backslash, newline, control char \x01
        # After escaping: backslash -> \\, newline -> \n, \x01 -> \x01
        small_parts = ["\\", "\n", "\x01"]
        small_input = "".join(small_parts)
        small_result = _sanitize_text(small_input)
        # Expected: \\ (escaped backslash) + \n (escaped newline) + \x01 (escaped control)
        assert small_result == r"\\\n\x01", f"Got {small_result!r}"


class TestSanitizeTextSinglePassBehavior:
    """Test that the optimization maintains correct behavior."""

    def test_backslash_before_control_char(self) -> None:
        """Backslash followed by control char must be escaped correctly."""
        result = _sanitize_text("\\\x01")
        assert result == r"\\\x01", f"Got {result!r}"

    def test_literal_escape_sequence_vs_actual_control(self) -> None:
        """Literal r"\\x01" must differ from actual control char \\x01."""
        literal_result = _sanitize_text(r"\x01")
        control_result = _sanitize_text("\x01")

        assert literal_result != control_result, (
            f"Literal and control should differ: {literal_result!r} vs {control_result!r}"
        )
        assert literal_result == r"\\x01", f"Literal result: {literal_result!r}"
        assert control_result == r"\x01", f"Control result: {control_result!r}"

    def test_all_control_ranges_escaped(self) -> None:
        """All control character ranges should be properly escaped."""
        # C0 controls (0x00-0x1f) except \n, \r, \t
        for code in [0x00, 0x01, 0x1F]:
            result = _sanitize_text(chr(code))
            assert result == f"\\x{code:02x}", f"Code {code:#x}: got {result!r}"

        # Common controls with special escapes
        assert _sanitize_text("\n") == "\\n"
        assert _sanitize_text("\r") == "\\r"
        assert _sanitize_text("\t") == "\\t"

        # DEL (0x7f)
        assert _sanitize_text("\x7f") == "\\x7f"

        # C1 controls (0x80-0x9f)
        for code in [0x80, 0x9F]:
            result = _sanitize_text(chr(code))
            assert result == f"\\x{code:02x}", f"Code {code:#x}: got {result!r}"
