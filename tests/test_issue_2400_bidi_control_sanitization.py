"""Regression tests for Issue #2400: Unicode bidirectional control character sanitization.

This test file ensures that Unicode bidirectional control characters (U+202A-U+202E, U+2066-U+2069)
are properly escaped to prevent trojan source spoofing attacks.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBidiControlSanitization:
    """Test that Unicode bidirectional control characters are properly escaped."""

    def test_sanitize_text_escapes_u202a_lre(self):
        """LEFT-TO-RIGHT EMBEDDING (U+202A) should be escaped."""
        # U+202A LRE - can start trojan source attacks
        result = _sanitize_text("hello\u202aTROLL")
        assert r"\u202a" in result
        assert "\u202a" not in result

    def test_sanitize_text_escapes_u202b_rle(self):
        """RIGHT-TO-LEFT EMBEDDING (U+202B) should be escaped."""
        # U+202B RLE
        result = _sanitize_text("hello\u202bTROLL")
        assert r"\u202b" in result
        assert "\u202b" not in result

    def test_sanitize_text_escapes_u202c_pdf(self):
        """POP DIRECTIONAL FORMAT (U+202C) should be escaped."""
        # U+202C PDF
        result = _sanitize_text("hello\u202cworld")
        assert r"\u202c" in result
        assert "\u202c" not in result

    def test_sanitize_text_escapes_u202d_lro(self):
        """LEFT-TO-RIGHT OVERRIDE (U+202D) should be escaped."""
        # U+202D LRO
        result = _sanitize_text("hello\u202dworld")
        assert r"\u202d" in result
        assert "\u202d" not in result

    def test_sanitize_text_escapes_u202e_rlo(self):
        """RIGHT-TO-LEFT OVERRIDE (U+202E) should be escaped."""
        # U+202E RLO - most dangerous bidi control char
        result = _sanitize_text("hello\u202eTROLL")
        assert r"\u202e" in result
        assert "\u202e" not in result

    def test_sanitize_text_escapes_u2066_lri(self):
        """LEFT-TO-RIGHT ISOLATE (U+2066) should be escaped."""
        # U+2066 LRI
        result = _sanitize_text("hello\u2066world")
        assert r"\u2066" in result
        assert "\u2066" not in result

    def test_sanitize_text_escapes_u2067_rli(self):
        """RIGHT-TO-LEFT ISOLATE (U+2067) should be escaped."""
        # U+2067 RLI
        result = _sanitize_text("hello\u2067world")
        assert r"\u2067" in result
        assert "\u2067" not in result

    def test_sanitize_text_escapes_u2068_fsi(self):
        """FIRST STRONG ISOLATE (U+2068) should be escaped."""
        # U+2068 FSI
        result = _sanitize_text("hello\u2068world")
        assert r"\u2068" in result
        assert "\u2068" not in result

    def test_sanitize_text_escapes_u2069_pdi(self):
        """POP DIRECTIONAL ISOLATE (U+2069) should be escaped."""
        # U+2069 PDI
        result = _sanitize_text("hello\u2069world")
        assert r"\u2069" in result
        assert "\u2069" not in result

    def test_sanitize_text_mixed_bidi_and_normal_text(self):
        """Test mixed bidi control chars and normal Unicode text."""
        result = _sanitize_text("normal text\u202eTROLL你好")
        # Should escape the bidi control char
        assert r"\u202e" in result
        # Should keep normal text
        assert "normal text" in result
        assert "你好" in result
        # Should not have raw bidi control char
        assert "\u202e" not in result

    def test_sanitize_text_normal_unicode_passes_through(self):
        """Normal Unicode text (Chinese, Japanese, emojis) passes through unchanged."""
        # Chinese characters
        assert _sanitize_text("你好世界") == "你好世界"
        # Japanese characters
        assert _sanitize_text("こんにちは") == "こんにちは"
        # Emojis
        assert _sanitize_text("Hello 🎉") == "Hello 🎉"
        # Accented characters
        assert _sanitize_text("café") == "café"
        # Mixed
        assert _sanitize_text("normal text 你好 🎉 café") == "normal text 你好 🎉 café"

    def test_format_todo_escapes_bidi_control_chars(self):
        """Todo format should escape bidi control characters."""
        todo = Todo(id=1, text="Buy milk\u202eFAKE", done=False)
        result = TodoFormatter.format_todo(todo)
        # Should contain escaped representation
        assert r"\u202e" in result
        # Should not contain raw bidi control char
        assert "\u202e" not in result

    def test_format_todo_with_normal_unicode(self):
        """Todo with normal Unicode should render correctly."""
        todo = Todo(id=1, text="Buy milk and eggs 你好 🎉", done=False)
        result = TodoFormatter.format_todo(todo)
        # Should contain the Unicode text
        assert "你好" in result
        assert "🎉" in result
        assert result == "[ ]   1 Buy milk and eggs 你好 🎉"

    def test_trojan_source_example(self):
        """Test a classic trojan source attack pattern."""
        # This is a classic trojan source pattern:
        # The RLO character makes the text appear reversed, hiding malicious code
        malicious = "code = true\u202eTROLL = false  # "
        result = _sanitize_text(malicious)
        # The RLO should be escaped
        assert r"\u202e" in result
        # Raw RLO should not be present
        assert "\u202e" not in result

    def test_all_bidi_ranges_escaped(self):
        """Test that all bidi control chars in U+202A-U+202E and U+2066-U+2069 are escaped."""
        # U+202A-U+202E range
        for code in [0x202a, 0x202b, 0x202c, 0x202d, 0x202e]:
            result = _sanitize_text(f"x{chr(code)}y")
            assert f"\\u{code:04x}" in result
            assert chr(code) not in result

        # U+2066-U+2069 range
        for code in [0x2066, 0x2067, 0x2068, 0x2069]:
            result = _sanitize_text(f"x{chr(code)}y")
            assert f"\\u{code:04x}" in result
            assert chr(code) not in result
