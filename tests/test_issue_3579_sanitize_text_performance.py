"""Regression tests for Issue #3579: Performance optimization for _sanitize_text.

This test file ensures that _sanitize_text is implemented using a single-pass
approach instead of multiple intermediate string creations via repeated replace() calls.

The previous implementation had O(n*m) complexity where n=input length and
m=number of replace operations, creating multiple intermediate strings.

The optimized implementation should process the input in a single pass.
"""

from __future__ import annotations

import inspect
import time

from flywheel.formatter import _sanitize_text


class TestSanitizeTextPerformance:
    """Test that _sanitize_text performs well on large inputs."""

    def test_sanitize_text_large_input_performance(self):
        """_sanitize_text should handle large inputs (100KB+) efficiently.

        This test verifies that the implementation doesn't create excessive
        intermediate strings. The optimized single-pass approach should
        complete within a reasonable time.
        """
        # Create a 100KB input with a mix of normal chars and chars needing escaping
        chunk = "Normal text with some \t tabs \n and \x01 control \x7f chars \\ backslash "
        large_input = chunk * (100 * 1024 // len(chunk))  # ~100KB

        # Measure time
        start = time.perf_counter()
        result = _sanitize_text(large_input)
        elapsed = time.perf_counter() - start

        # Should complete in reasonable time (< 1 second for 100KB)
        assert elapsed < 1.0, f"_sanitize_text took {elapsed:.3f}s for 100KB input - too slow!"

        # Verify correctness - result should be longer than input due to escapes
        assert len(result) > len(large_input)
        # Verify no control chars remain unescaped
        assert "\x01" not in result
        assert "\x7f" not in result
        assert "\t" not in result
        assert "\n" not in result

    def test_sanitize_text_uses_single_pass_approach(self):
        """Verify _sanitize_text uses single-pass approach, not repeated replace().

        This test inspects the source code to ensure the implementation doesn't
        use the anti-pattern of repeated str.replace() calls which create
        O(n*m) intermediate strings.
        """
        source = inspect.getsource(_sanitize_text)

        # The old anti-pattern used this pattern:
        # for char, escaped in replacements:
        #     text = text.replace(char, escaped)
        #
        # This creates O(n*m) intermediate strings and should NOT be used.
        # We check that the loop doesn't contain replace() calls on the accumulating text.

        # Count how many times we do replace on the main text variable
        # A proper single-pass implementation should iterate over characters,
        # not use multiple replace() calls on the whole string.
        lines = source.split('\n')

        # Check that we don't have a pattern like: text = text.replace(...)
        # which creates intermediate strings
        replace_on_text_pattern = False
        for line in lines:
            stripped = line.strip()
            # Detect the anti-pattern: assigning result of replace back to a variable
            # that was used as the previous replace target, within a loop
            if (
                '.replace(' in stripped
                and '=' in stripped
                and 'for ' in source[source.find(stripped) - 100 : source.find(stripped)]
            ):
                replace_on_text_pattern = True
                break

        assert not replace_on_text_pattern, (
            "Implementation uses repeated replace() in a loop, which creates "
            "O(n*m) intermediate strings. Use single-pass iteration instead."
        )

    def test_sanitize_text_preserves_correctness(self):
        """Ensure the optimized implementation still produces correct results."""
        # Test all the escaping cases in one comprehensive test
        test_input = (
            "Normal\\text\n"  # backslash + newline
            "\r\t"  # carriage return + tab
            "\x00\x01\x1f"  # control chars 0x00-0x1f
            "\x7f"  # DEL
            "\x80\x9f"  # C1 control chars
            "End"
        )
        result = _sanitize_text(test_input)

        # Verify expected escapes
        assert "\\\\" in result  # backslash escaped
        assert "\\n" in result  # newline escaped
        assert "\\r" in result  # carriage return escaped
        assert "\\t" in result  # tab escaped
        assert "\\x00" in result  # null escaped
        assert "\\x01" in result  # SOH escaped
        assert "\\x1f" in result  # US escaped
        assert "\\x7f" in result  # DEL escaped
        assert "\\x80" in result  # C1 PAD escaped
        assert "\\x9f" in result  # C1 APC escaped
        assert "End" in result  # Normal text preserved


class TestSanitizeTextCorrectnessMaintained:
    """Ensure existing functionality is preserved after optimization."""

    def test_empty_string(self):
        """Empty string should remain empty."""
        assert _sanitize_text("") == ""

    def test_plain_text_unchanged(self):
        """Text without control characters should pass through unchanged."""
        text = "Hello, World! 123 @#$%^&*()"
        assert _sanitize_text(text) == text

    def test_backslash_escaping(self):
        """Backslashes should be escaped to double backslashes."""
        assert _sanitize_text("\\") == "\\\\"
        assert _sanitize_text("C:\\path") == "C:\\\\path"

    def test_control_char_escaping(self):
        """Control characters should be properly escaped."""
        assert _sanitize_text("\x01") == "\\x01"
        assert _sanitize_text("\x00") == "\\x00"
        assert _sanitize_text("\x1f") == "\\x1f"

    def test_common_escapes(self):
        """Common escape sequences (\\n, \\r, \\t) should work correctly."""
        assert _sanitize_text("\n") == "\\n"
        assert _sanitize_text("\r") == "\\r"
        assert _sanitize_text("\t") == "\\t"

    def test_del_and_c1_escaping(self):
        """DEL (0x7f) and C1 (0x80-0x9f) should be escaped."""
        assert _sanitize_text("\x7f") == "\\x7f"
        assert _sanitize_text("\x80") == "\\x80"
        assert _sanitize_text("\x9f") == "\\x9f"

    def test_unicode_preserved(self):
        """Unicode text should pass through unchanged."""
        assert _sanitize_text("こんにちは") == "こんにちは"
        assert _sanitize_text("café") == "café"
        assert _sanitize_text("🎉") == "🎉"
