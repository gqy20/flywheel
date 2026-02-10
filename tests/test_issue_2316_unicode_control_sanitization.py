"""Regression tests for Issue #2316: Unicode bidirectional control character sanitization.

This test file ensures that Unicode bidirectional override characters and zero-width
characters are properly escaped to prevent text spoofing attacks.

The following Unicode control characters should be escaped:
- U+202A: LEFT-TO-RIGHT EMBEDDING
- U+202B: RIGHT-TO-LEFT EMBEDDING
- U+202C: POP DIRECTIONAL FORMATTING
- U+202D: LEFT-TO-RIGHT OVERRIDE
- U+202E: RIGHT-TO-LEFT OVERRIDE
- U+200B: ZERO WIDTH SPACE
- U+200C: ZERO WIDTH NON-JOINER
- U+200D: ZERO WIDTH JOINER
"""

from flywheel.formatter import _sanitize_text


class TestUnicodeBidirectionalControlSanitization:
    """Test that Unicode bidirectional control characters are properly escaped."""

    def test_sanitize_text_escapes_rtl_override_u202e(self):
        """Test that U+202E (RTL override) is escaped."""
        # U+202E is RIGHT-TO-LEFT OVERRIDE - can flip text direction
        result = _sanitize_text("test\u202e")
        assert r"\u202e" in result
        assert "\u202e" not in result

    def test_sanitize_text_escapes_ltr_override_u202d(self):
        """Test that U+202D (LTR override) is escaped."""
        # U+202D is LEFT-TO-RIGHT OVERRIDE
        result = _sanitize_text("test\u202d")
        assert r"\u202d" in result
        assert "\u202d" not in result

    def test_sanitize_text_escapes_zero_width_space_u200b(self):
        """Test that U+200B (zero-width space) is escaped."""
        # U+200B is ZERO WIDTH SPACE - invisible character
        result = _sanitize_text("test\u200b")
        assert r"\u200b" in result
        assert "\u200b" not in result

    def test_sanitize_text_escapes_rtl_embedding_u202b(self):
        """Test that U+202B (RTL embedding) is escaped."""
        # U+202B is RIGHT-TO-LEFT EMBEDDING
        result = _sanitize_text("test\u202b")
        assert r"\u202b" in result
        assert "\u202b" not in result

    def test_sanitize_text_escapes_ltr_embedding_u202a(self):
        """Test that U+202A (LTR embedding) is escaped."""
        # U+202A is LEFT-TO-RIGHT EMBEDDING
        result = _sanitize_text("test\u202a")
        assert r"\u202a" in result
        assert "\u202a" not in result

    def test_sanitize_text_escapes_pop_directional_u202c(self):
        """Test that U+202C (pop directional formatting) is escaped."""
        # U+202C is POP DIRECTIONAL FORMATTING
        result = _sanitize_text("test\u202c")
        assert r"\u202c" in result
        assert "\u202c" not in result

    def test_sanitize_text_escapes_zero_width_non_joiner_u200c(self):
        """Test that U+200C (zero-width non-joiner) is escaped."""
        # U+200C is ZERO WIDTH NON-JOINER
        result = _sanitize_text("test\u200c")
        assert r"\u200c" in result
        assert "\u200c" not in result

    def test_sanitize_text_escapes_zero_width_joiner_u200d(self):
        """Test that U+200D (zero-width joiner) is escaped."""
        # U+200D is ZERO WIDTH JOINER
        result = _sanitize_text("test\u200d")
        assert r"\u200d" in result
        assert "\u200d" not in result

    def test_sanitize_text_spoofing_attack_example(self):
        """Test a realistic text spoofing attack scenario.

        Example attack: "admin\u202e: characters can flip text to spoof
        display as "user: admin" instead of "admin: user".
        """
        # This would display as "mock: admin" (reversed) without proper escaping
        malicious = "admin\u202emoc"
        result = _sanitize_text(malicious)
        assert r"\u202e" in result
        assert "\u202e" not in result

    def test_sanitize_text_mixed_unicode_controls(self):
        """Test multiple Unicode control characters in one string."""
        text = "a\u202eb\u200bc\u202dd"
        result = _sanitize_text(text)
        # All should be escaped
        assert r"\u202e" in result
        assert r"\u200b" in result
        assert r"\u202d" in result
        # Original control chars should not be present
        assert "\u202e" not in result
        assert "\u200b" not in result
        assert "\u202d" not in result

    def test_sanitize_text_normal_arabic_passes_through(self):
        """Test that normal Arabic text is NOT escaped.

        We only want to escape control characters, not legitimate
        right-to-left text in Arabic, Hebrew, etc.
        """
        # Normal Arabic text should pass through unchanged
        assert _sanitize_text("مرحبا") == "مرحبا"
        # Normal Hebrew text should pass through unchanged
        assert _sanitize_text("שלום") == "שלום"

    def test_sanitize_text_normal_unicode_passes_through(self):
        """Test that normal Unicode text without control chars passes through."""
        # Various normal Unicode characters should be unchanged
        assert _sanitize_text("Hello 世界") == "Hello 世界"
        assert _sanitize_text("Café") == "Café"
        assert _sanitize_text("emoji 🎉") == "emoji 🎉"

    def test_sanitize_text_ascii_controls_still_work(self):
        """Test that ASCII control character escaping still works."""
        # Existing functionality for ASCII controls should still work
        assert _sanitize_text("test\n") == r"test\n"
        assert _sanitize_text("test\t") == r"test\t"
        assert _sanitize_text("test\x00") == r"test\x00"
