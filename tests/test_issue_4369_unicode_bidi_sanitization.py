"""Regression tests for Issue #4369: Unicode bidirectional text control character sanitization.

This test file ensures that Unicode bidirectional text control characters are properly
escaped to prevent visual text deception attacks (e.g., using RLO to make "exe.txt"
appear as "txt.exe").

Unicode bidirectional control characters to escape:
- U+202A-U+202E: LRE, RLE, PDF, LRO, RLO (bidirectional formatting)
- U+2066-U+2069: LRI, RLI, FSI, PDI (bidirectional isolates)
- U+2028-U+2029: Line separator, Paragraph separator
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestUnicodeBidirectionalSanitization:
    """Test that Unicode bidirectional text control characters are properly escaped."""

    def test_sanitize_text_escapes_rlo_u202e(self):
        """RLO (Right-to-Left Override, U+202E) should be escaped.

        This is the most dangerous character for visual deception attacks.
        Attack vector: '\u202eexe.txt\u202c' displays as 'txt.exe'
        """
        result = _sanitize_text("\u202e")
        assert result == r"\u202e", f"Expected r'\\u202e' but got {result!r}"
        # The raw RLO character should NOT be in the output
        assert "\u202e" not in result

    def test_sanitize_text_escapes_lro_u202d(self):
        """LRO (Left-to-Right Override, U+202D) should be escaped."""
        result = _sanitize_text("\u202d")
        assert result == r"\u202d", f"Expected r'\\u202d' but got {result!r}"
        assert "\u202d" not in result

    def test_sanitize_text_escapes_pdf_u202c(self):
        """PDF (Pop Directional Format, U+202C) should be escaped."""
        result = _sanitize_text("\u202c")
        assert result == r"\u202c", f"Expected r'\\u202c' but got {result!r}"
        assert "\u202c" not in result

    def test_sanitize_text_escapes_lre_u202a(self):
        """LRE (Left-to-Right Embedding, U+202A) should be escaped."""
        result = _sanitize_text("\u202a")
        assert result == r"\u202a", f"Expected r'\\u202a' but got {result!r}"
        assert "\u202a" not in result

    def test_sanitize_text_escapes_rle_u202b(self):
        """RLE (Right-to-Left Embedding, U+202B) should be escaped."""
        result = _sanitize_text("\u202b")
        assert result == r"\u202b", f"Expected r'\\u202b' but got {result!r}"
        assert "\u202b" not in result

    def test_sanitize_text_escapes_line_separator_u2028(self):
        """Line Separator (U+2028) should be escaped."""
        result = _sanitize_text("\u2028")
        assert result == r"\u2028", f"Expected r'\\u2028' but got {result!r}"
        assert "\u2028" not in result

    def test_sanitize_text_escapes_paragraph_separator_u2029(self):
        """Paragraph Separator (U+2029) should be escaped."""
        result = _sanitize_text("\u2029")
        assert result == r"\u2029", f"Expected r'\\u2029' but got {result!r}"
        assert "\u2029" not in result

    def test_sanitize_text_escapes_lri_u2066(self):
        """LRI (Left-to-Right Isolate, U+2066) should be escaped."""
        result = _sanitize_text("\u2066")
        assert result == r"\u2066", f"Expected r'\\u2066' but got {result!r}"
        assert "\u2066" not in result

    def test_sanitize_text_escapes_rli_u2067(self):
        """RLI (Right-to-Left Isolate, U+2067) should be escaped."""
        result = _sanitize_text("\u2067")
        assert result == r"\u2067", f"Expected r'\\u2067' but got {result!r}"
        assert "\u2067" not in result

    def test_sanitize_text_escapes_fsi_u2068(self):
        """FSI (First Strong Isolate, U+2068) should be escaped."""
        result = _sanitize_text("\u2068")
        assert result == r"\u2068", f"Expected r'\\u2068' but got {result!r}"
        assert "\u2068" not in result

    def test_sanitize_text_escapes_pdi_u2069(self):
        """PDI (Pop Directional Isolate, U+2069) should be escaped."""
        result = _sanitize_text("\u2069")
        assert result == r"\u2069", f"Expected r'\\u2069' but got {result!r}"
        assert "\u2069" not in result

    def test_rlo_attack_vector_exe_txt(self):
        """Test the RLO attack vector: '\u202eexe.txt\u202c' should be fully escaped.

        This attack would display 'exe.txt' as 'txt.exe' in many renderers,
        potentially tricking users into executing malicious files.
        """
        attack_string = "\u202eexe.txt\u202c"
        result = _sanitize_text(attack_string)

        # Should be escaped, not the raw characters
        assert result == r"\u202eexe.txt\u202c", f"Attack not neutralized: got {result!r}"

        # Raw RLO/PDF should NOT be present
        assert "\u202e" not in result
        assert "\u202c" not in result

    def test_format_todo_with_rlo_in_text(self):
        """TodoFormatter should escape RLO characters in todo text."""
        todo = Todo(id=1, text="Normal task\u202efake.txt", done=False)
        result = TodoFormatter.format_todo(todo)

        # Should contain escaped representation
        assert r"\u202e" in result

        # Should NOT contain raw RLO
        assert "\u202e" not in result

        # Full expected output
        assert result == r"[ ]   1 Normal task\u202efake.txt"

    def test_multiple_bidi_chars_in_text(self):
        """Multiple bidirectional control characters should all be escaped."""
        text = "Start\u202e\u2066\u202cEnd"
        result = _sanitize_text(text)

        assert result == r"Start\u202e\u2066\u202cEnd"
        assert "\u202e" not in result
        assert "\u2066" not in result
        assert "\u202c" not in result

    def test_mixed_ascii_control_and_bidi_chars(self):
        """Mix of ASCII control chars and Unicode bidi chars should both be escaped."""
        # Mix of: newline, RLO, ESC, LRI
        text = "line1\n\u202e\x1b\u2066"
        result = _sanitize_text(text)

        # All should be escaped
        assert result == r"line1\n\u202e\x1b\u2066"

    def test_bidi_with_backslash_in_text(self):
        """Backslash + bidi char should both be escaped properly."""
        # Literal backslash followed by RLO
        text = "\\path\u202e"
        result = _sanitize_text(text)

        # Backslash becomes \\, RLO becomes \u202e
        assert result == r"\\path\u202e"

    def test_normal_unicode_unchanged(self):
        """Normal Unicode text (Chinese, emoji, etc.) should pass through unchanged."""
        # Japanese
        assert _sanitize_text("こんにちは") == "こんにちは"
        # Chinese
        assert _sanitize_text("你好世界") == "你好世界"
        # Arabic (valid right-to-left text, not a control char)
        assert _sanitize_text("مرحبا") == "مرحبا"
        # Hebrew
        assert _sanitize_text("שלום") == "שלום"
        # Emoji
        assert _sanitize_text("🎉🎊") == "🎉🎊"


class TestBidirectionalRangeCoverage:
    """Test that the full Unicode bidirectional ranges are covered."""

    def test_full_range_202a_to_202e(self):
        """Test all characters in U+202A to U+202E range."""
        for code in range(0x202A, 0x202F):
            char = chr(code)
            result = _sanitize_text(char)
            # All should be escaped (not the raw character)
            assert char not in result, f"U+{code:04X} was not escaped"
            # Should contain the escape sequence
            assert f"\\u{code:04x}" in result, f"U+{code:04X} should escape to \\u{code:04x}"

    def test_full_range_2066_to_2069(self):
        """Test all characters in U+2066 to U+2069 range."""
        for code in range(0x2066, 0x206A):
            char = chr(code)
            result = _sanitize_text(char)
            # All should be escaped
            assert char not in result, f"U+{code:04X} was not escaped"
            assert f"\\u{code:04x}" in result, f"U+{code:04X} should escape to \\u{code:04x}"
