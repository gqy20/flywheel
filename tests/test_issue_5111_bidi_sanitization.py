"""Tests for Unicode BiDi character sanitization (Issue #5111).

Unicode Bidirectional (BiDi) override characters can cause text display
manipulation attacks. For example, 'print("Read \u202eCMD.exe\u202c")' may
appear as 'Read exe.CMD' instead of the actual text.

These characters should be sanitized to prevent security issues.
"""

from flywheel.formatter import _sanitize_text


class TestBiDiSanitization:
    """Test that Unicode BiDi characters are properly escaped."""

    def test_sanitize_text_escapes_right_to_left_override_u202e(self):
        """Test that RIGHT-TO-LEFT OVERRIDE (U+202E) is escaped."""
        # U+202E is the most dangerous BiDi character
        result = _sanitize_text("Hello\u202eWorld")
        assert "\u202e" not in result
        assert "\\u202e" in result

    def test_sanitize_text_escapes_bidi_range_u202a_to_u202e(self):
        """Test that the full BiDi range U+202A-U+202E is escaped."""
        # U+202A: LEFT-TO-RIGHT EMBEDDING
        assert _sanitize_text("\u202a") == "\\u202a"
        # U+202B: RIGHT-TO-LEFT EMBEDDING
        assert _sanitize_text("\u202b") == "\\u202b"
        # U+202C: POP DIRECTIONAL FORMATTING
        assert _sanitize_text("\u202c") == "\\u202c"
        # U+202D: LEFT-TO-RIGHT OVERRIDE
        assert _sanitize_text("\u202d") == "\\u202d"
        # U+202E: RIGHT-TO-LEFT OVERRIDE
        assert _sanitize_text("\u202e") == "\\u202e"

    def test_sanitize_text_escapes_bidi_isolate_range_u2066_to_u2069(self):
        """Test that the BiDi isolate range U+2066-U+2069 is escaped."""
        # U+2066: LEFT-TO-RIGHT ISOLATE
        assert _sanitize_text("\u2066") == "\\u2066"
        # U+2067: RIGHT-TO-LEFT ISOLATE
        assert _sanitize_text("\u2067") == "\\u2067"
        # U+2068: FIRST STRONG ISOLATE
        assert _sanitize_text("\u2068") == "\\u2068"
        # U+2069: POP DIRECTIONAL ISOLATE
        assert _sanitize_text("\u2069") == "\\u2069"

    def test_sanitize_text_escapes_invisible_formatting_range_u200b_to_u200f(self):
        """Test that invisible formatting range U+200B-U+200F is escaped."""
        # U+200B: ZERO WIDTH SPACE
        assert _sanitize_text("\u200b") == "\\u200b"
        # U+200C: ZERO WIDTH NON-JOINER
        assert _sanitize_text("\u200c") == "\\u200c"
        # U+200D: ZERO WIDTH JOINER
        assert _sanitize_text("\u200d") == "\\u200d"
        # U+200E: LEFT-TO-RIGHT MARK
        assert _sanitize_text("\u200e") == "\\u200e"
        # U+200F: RIGHT-TO-LEFT MARK
        assert _sanitize_text("\u200f") == "\\u200f"

    def test_sanitize_text_escapes_invisible_operators_u2060_to_u2064(self):
        """Test that invisible operators range U+2060-U+2064 is escaped."""
        # U+2060: WORD JOINER
        assert _sanitize_text("\u2060") == "\\u2060"
        # U+2061: FUNCTION APPLICATION
        assert _sanitize_text("\u2061") == "\\u2061"
        # U+2062: INVISIBLE TIMES
        assert _sanitize_text("\u2062") == "\\u2062"
        # U+2063: INVISIBLE SEPARATOR
        assert _sanitize_text("\u2063") == "\\u2063"
        # U+2064: INVISIBLE PLUS
        assert _sanitize_text("\u2064") == "\\u2064"

    def test_sanitize_text_escapes_bom_feff(self):
        """Test that BOM/ZWNBSP (U+FEFF) is escaped."""
        assert _sanitize_text("\ufeff") == "\\ufeff"

    def test_sanitize_text_bidi_attack_scenario(self):
        """Test a realistic BiDi attack scenario."""
        # Simulate the attack: 'EXEC\u202eNOT\u202c.exe'
        # Without sanitization, this could appear as 'EXEC.exeNOT'
        malicious = "EXEC\u202eNOT\u202c.exe"
        result = _sanitize_text(malicious)
        # Should not contain raw BiDi characters
        assert "\u202e" not in result
        assert "\u202c" not in result
        # Should contain escaped representations
        assert "\\u202e" in result
        assert "\\u202c" in result

    def test_sanitize_text_bidi_with_other_controls(self):
        """Test that BiDi chars are escaped alongside other control characters."""
        # Mix of C0, BiDi, and normal text
        result = _sanitize_text("a\u202eb\x01c")
        assert "\u202e" not in result
        assert "\\u202e" in result
        assert "\\x01" in result

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes BiDi control characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        todo = Todo(id=1, text="Read\u202eCMD.exe", done=False)
        result = TodoFormatter.format_todo(todo)
        # Should contain escaped representation, not raw BiDi
        assert "\u202e" not in result
        assert "\\u202e" in result

    def test_unicode_text_without_bidi_passes_through(self):
        """Test that valid Unicode text without BiDi chars is not affected."""
        # These should all pass through unchanged
        assert _sanitize_text("こんにちは") == "こんにちは"
        assert _sanitize_text("café") == "café"
        assert _sanitize_text("🎉") == "🎉"
        assert _sanitize_text("你好") == "你好"
        # Regular punctuation and symbols should pass through
        assert _sanitize_text("€") == "€"  # Euro sign
        assert _sanitize_text("→") == "→"  # Arrow
