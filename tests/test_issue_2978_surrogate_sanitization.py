"""Tests for surrogate character sanitization (Issue #2978).

Lone surrogate characters (0xD800-0xDFFF) are invalid in UTF-8 encoding
when appearing alone and can cause UnicodeEncodeError. They should be
sanitized to prevent encoding errors.
"""

from flywheel.formatter import _sanitize_text


class TestSurrogateSanitization:
    """Test that lone surrogate characters (0xD800-0xDFFF) are properly escaped."""

    def test_sanitize_text_escapes_high_surrogate_d800(self):
        """Test that high surrogate start (0xD800) is escaped."""
        # Surrogates can be created using chr() with surrogates pass error handler
        # or by using \ud800 escape in string literal
        text_with_surrogate = "text\ud800after"
        result = _sanitize_text(text_with_surrogate)
        # D800 = 55296 in decimal, escaped as \xd800
        assert result == r"text\xd800after"
        # Verify output can be encoded to UTF-8
        result.encode("utf-8")

    def test_sanitize_text_escapes_low_surrogate_dfff(self):
        """Test that low surrogate end (0xDFFF) is escaped."""
        text_with_surrogate = "normal\udfffend"
        result = _sanitize_text(text_with_surrogate)
        # Verify output can be encoded to UTF-8
        result.encode("utf-8")

    def test_sanitize_text_escapes_full_surrogate_range(self):
        """Test that the full surrogate range (0xD800-0xDFFF) is escaped."""
        # Test start of surrogate range (0xD800 - high surrogate start)
        assert "\ud800" not in _sanitize_text("test\ud800")
        # Test end of surrogate range (0xDFFF - low surrogate end)
        assert "\udfff" not in _sanitize_text("test\udfff")
        # All results should be encodable to UTF-8
        _sanitize_text("test\ud800").encode("utf-8")
        _sanitize_text("test\udfff").encode("utf-8")

    def test_sanitize_text_surrogate_with_other_controls(self):
        """Test that surrogates are escaped alongside other control characters."""
        # Mix of C0, C1, DEL, and surrogates
        result = _sanitize_text("a\x01b\ud800c\x7fd")
        # Verify no surrogates remain
        for char in result:
            code = ord(char)
            assert not (0xD800 <= code <= 0xDFFF), f"Surrogate {hex(code)} found in result"
        # Verify result is encodable
        result.encode("utf-8")

    def test_format_todo_escapes_surrogates(self):
        """Test that format_todo properly escapes surrogate characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        todo = Todo(id=1, text="Buy milk\ud800", done=False)
        result = TodoFormatter.format_todo(todo)
        # Verify no surrogates in output
        for char in result:
            code = ord(char)
            assert not (0xD800 <= code <= 0xDFFF), f"Surrogate {hex(code)} found in result"
        # Verify result is encodable to UTF-8
        result.encode("utf-8")

    def test_sanitize_text_output_is_utf8_encodable(self):
        """Test that sanitized output can always be encoded to UTF-8."""
        # Test with various surrogate values
        test_cases = [
            "\ud800",  # High surrogate start
            "\udbff",  # High surrogate end
            "\udc00",  # Low surrogate start
            "\udfff",  # Low surrogate end
            "prefix\ud800suffix",
            "\udfff\ud800\udc00",
        ]
        for text in test_cases:
            result = _sanitize_text(text)
            # This should NOT raise UnicodeEncodeError
            result.encode("utf-8")


class TestSurrogateSanitizationFailure:
    """Test that demonstrates the current bug (should fail before fix)."""

    def test_surrogate_causes_encoding_error_before_fix(self):
        """Test that shows surrogates pass through unescaped, causing issues."""
        # This test demonstrates the bug - before fix, this would pass a surrogate through
        # After fix, the surrogate should be escaped
        text_with_surrogate = "\ud800"
        result = _sanitize_text(text_with_surrogate)
        # The result should NOT contain any surrogate characters
        # (they should be escaped)
        for char in result:
            code = ord(char)
            assert not (0xD800 <= code <= 0xDFFF), (
                f"Lone surrogate U+{code:04X} was not escaped. "
                f"This will cause UnicodeEncodeError when encoding to UTF-8."
            )
