"""Tests for Unicode bidirectional text control character sanitization (Issue #4369).

Unicode bidirectional text control characters (U+202A-U+202E, U+2066-U+2069)
and line/paragraph separators (U+2028, U+2029) can be used for visual spoofing
attacks. These characters should be sanitized to prevent terminal output
manipulation.

References:
- U+202A-U+202E: Bidirectional text formatting (LRE, RLE, PDF, LRO, RLO)
- U+2066-U+2069: Isolate formatters (LRI, RLI, FSI, PDI)
- U+2028: Line separator
- U+2029: Paragraph separator
- U+200E-U+200F: LRM, RLM (left-to-right/right-to-left marks)
"""

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestUnicodeBidiSanitization:
    """Test that Unicode bidirectional control characters are properly escaped."""

    def test_sanitize_text_escapes_rlo_u202e(self):
        """Test that U+202E (RLO - Right-to-Left Override) is escaped.

        RLO is the most dangerous bidi character for visual spoofing attacks.
        Input: '\\u202eexe.txt\\u202c' would display as 'txt.exe' without escaping.
        """
        assert _sanitize_text("\u202e") == r"\u202e"

    def test_sanitize_text_escapes_lro_u202d(self):
        """Test that U+202D (LRO - Left-to-Right Override) is escaped."""
        assert _sanitize_text("\u202d") == r"\u202d"

    def test_sanitize_text_escapes_pdf_u202c(self):
        """Test that U+202C (PDF - Pop Directional Formatting) is escaped."""
        assert _sanitize_text("\u202c") == r"\u202c"

    def test_sanitize_text_escapes_lre_u202a(self):
        """Test that U+202A (LRE - Left-to-Right Embedding) is escaped."""
        assert _sanitize_text("\u202a") == r"\u202a"

    def test_sanitize_text_escapes_rle_u202b(self):
        """Test that U+202B (RLE - Right-to-Left Embedding) is escaped."""
        assert _sanitize_text("\u202b") == r"\u202b"

    def test_sanitize_text_escapes_line_separator_u2028(self):
        """Test that U+2028 (Line Separator) is escaped."""
        assert _sanitize_text("\u2028") == r"\u2028"

    def test_sanitize_text_escapes_paragraph_separator_u2029(self):
        """Test that U+2029 (Paragraph Separator) is escaped."""
        assert _sanitize_text("\u2029") == r"\u2029"

    def test_sanitize_text_escapes_lri_u2066(self):
        """Test that U+2066 (LRI - Left-to-Right Isolate) is escaped."""
        assert _sanitize_text("\u2066") == r"\u2066"

    def test_sanitize_text_escapes_rli_u2067(self):
        """Test that U+2067 (RLI - Right-to-Left Isolate) is escaped."""
        assert _sanitize_text("\u2067") == r"\u2067"

    def test_sanitize_text_escapes_fsi_u2068(self):
        """Test that U+2068 (FSI - First Strong Isolate) is escaped."""
        assert _sanitize_text("\u2068") == r"\u2068"

    def test_sanitize_text_escapes_pdi_u2069(self):
        """Test that U+2069 (PDI - Pop Directional Isolate) is escaped."""
        assert _sanitize_text("\u2069") == r"\u2069"

    def test_sanitize_text_escapes_lrm_u200e(self):
        """Test that U+200E (LRM - Left-to-Right Mark) is escaped."""
        assert _sanitize_text("\u200e") == r"\u200e"

    def test_sanitize_text_escapes_rlm_u200f(self):
        """Test that U+200F (RLM - Right-to-Left Mark) is escaped."""
        assert _sanitize_text("\u200f") == r"\u200f"


class TestUnicodeBidiRloAttackVector:
    """Test specific RLO visual spoofing attack scenarios."""

    def test_rlo_attack_vector_exe_txt(self):
        """Test the classic RLO attack: '\\u202eexe.txt\\u202c' should not display as 'txt.exe'.

        Without sanitization, '\\u202eexe.txt\\u202c' would display visually as 'txt.exe',
        tricking the user into thinking it's a text file when it's actually an executable.
        """
        # The RLO attack string
        malicious = "\u202eexe.txt\u202c"

        result = _sanitize_text(malicious)

        # The result should contain escaped unicode, not the raw characters
        assert "\u202e" not in result
        assert "\u202c" not in result

        # The result should show the escape sequences
        assert r"\u202e" in result
        assert r"\u202c" in result

        # Verify the exact expected output
        assert result == r"\u202eexe.txt\u202c"

    def test_rlo_attack_with_backslash_collision(self):
        """Test that literal backslash-unicode text is distinguishable from actual bidi chars.

        This ensures that literal text r'\\u202e' doesn't collide with actual U+202E.
        """
        # Actual bidi character
        actual_bidi_output = _sanitize_text("\u202e")

        # Literal text that looks like the escape sequence
        literal_unicode_text_output = _sanitize_text(r"\u202e")

        # These MUST be different to prevent collision attacks
        assert actual_bidi_output != literal_unicode_text_output, (
            "SECURITY: Bidi character and literal text produced identical output!"
        )


class TestUnicodeBidiInTodoFormatter:
    """Test that TodoFormatter properly escapes bidi characters."""

    def test_format_todo_escapes_rlo(self):
        """TodoFormatter should escape RLO characters in todo text."""
        todo = Todo(id=1, text="\u202emalicious.txt\u202c", done=False)
        result = TodoFormatter.format_todo(todo)

        # Raw bidi chars should not appear in output
        assert "\u202e" not in result
        assert "\u202c" not in result

        # Escaped sequences should appear instead
        assert r"\u202e" in result
        assert r"\u202c" in result

    def test_format_todo_with_mixed_bidi_and_normal_text(self):
        """TodoFormatter should handle mixed normal text and bidi characters."""
        todo = Todo(id=2, text="Hello \u202eworld\u202c!", done=False)
        result = TodoFormatter.format_todo(todo)

        assert r"\u202e" in result
        assert r"\u202c" in result
        assert "Hello " in result
        assert "world" in result
        assert "!" in result


class TestUnicodeBidiComprehensive:
    """Comprehensive tests for Unicode bidi character ranges."""

    def test_all_bidi_format_chars_are_escaped(self):
        """Test that all bidirectional formatting chars (U+202A-U+202E) are escaped."""
        bidi_format_chars = [
            ("\u202a", r"\u202a"),  # LRE
            ("\u202b", r"\u202b"),  # RLE
            ("\u202c", r"\u202c"),  # PDF
            ("\u202d", r"\u202d"),  # LRO
            ("\u202e", r"\u202e"),  # RLO
        ]

        for char, expected in bidi_format_chars:
            assert _sanitize_text(char) == expected, f"Char {char!r} not escaped correctly"

    def test_all_bidi_isolate_chars_are_escaped(self):
        """Test that all bidirectional isolate chars (U+2066-U+2069) are escaped."""
        bidi_isolate_chars = [
            ("\u2066", r"\u2066"),  # LRI
            ("\u2067", r"\u2067"),  # RLI
            ("\u2068", r"\u2068"),  # FSI
            ("\u2069", r"\u2069"),  # PDI
        ]

        for char, expected in bidi_isolate_chars:
            assert _sanitize_text(char) == expected, f"Char {char!r} not escaped correctly"

    def test_line_and_paragraph_separators_are_escaped(self):
        """Test that line/paragraph separators (U+2028-U+2029) are escaped."""
        separators = [
            ("\u2028", r"\u2028"),  # Line Separator
            ("\u2029", r"\u2029"),  # Paragraph Separator
        ]

        for char, expected in separators:
            assert _sanitize_text(char) == expected, f"Char {char!r} not escaped correctly"

    def test_directional_marks_are_escaped(self):
        """Test that directional marks (U+200E-U+200F) are escaped."""
        marks = [
            ("\u200e", r"\u200e"),  # LRM
            ("\u200f", r"\u200f"),  # RLM
        ]

        for char, expected in marks:
            assert _sanitize_text(char) == expected, f"Char {char!r} not escaped correctly"

    def test_normal_unicode_text_not_affected(self):
        """Normal Unicode text (Chinese, Arabic, emoji) should pass through unchanged."""
        # Chinese characters
        assert _sanitize_text("你好") == "你好"

        # Arabic text (should display right-to-left, but chars are not bidi controls)
        assert _sanitize_text("مرحبا") == "مرحبا"

        # Emoji
        assert _sanitize_text("🎉") == "🎉"

        # Mixed text
        assert _sanitize_text("Hello 世界!") == "Hello 世界!"
