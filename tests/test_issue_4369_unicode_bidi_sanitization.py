"""Tests for Unicode bidirectional control character sanitization (Issue #4369).

Unicode bidirectional text control characters (U+202A-U+202E, U+2066-U+2069)
can be used for visual spoofing attacks. For example, U+202E (RLO) reverses
the display order of subsequent characters, making "exe\u202etxt\u202c" appear
as "txt.exe" in terminals. These should be escaped to prevent such attacks.

Additionally, Unicode line/paragraph separators (U+2028, U+2029) should also
be escaped as they can cause unexpected line breaks.
"""

from flywheel.formatter import _sanitize_text


class TestUnicodeBidiSanitization:
    """Test that Unicode bidirectional control characters are properly escaped."""

    def test_sanitize_text_escapes_rlo_character(self):
        """Test that U+202E (RLO - Right-to-Left Override) is escaped."""
        # RLO reverses display order - major security risk
        assert _sanitize_text("\u202e") == r"\u202e"
        assert "exe\u202etxt" not in _sanitize_text("exe\u202etxt")
        assert r"\u202e" in _sanitize_text("exe\u202etxt")

    def test_sanitize_text_escapes_lro_character(self):
        """Test that U+202D (LRO - Left-to-Right Override) is escaped."""
        assert _sanitize_text("\u202d") == r"\u202d"
        assert _sanitize_text("text\u202dmore") == r"text\u202dmore"

    def test_sanitize_text_escapes_pdf_character(self):
        """Test that U+202C (PDF - Pop Directional Format) is escaped."""
        assert _sanitize_text("\u202c") == r"\u202c"

    def test_sanitize_text_escapes_bidi_embedding_chars(self):
        """Test that U+202A (LRE) and U+202B (RLE) are escaped."""
        # LRE - Left-to-Right Embedding
        assert _sanitize_text("\u202a") == r"\u202a"
        # RLE - Right-to-Left Embedding
        assert _sanitize_text("\u202b") == r"\u202b"

    def test_sanitize_text_escapes_bidi_isolate_chars(self):
        """Test that U+2066-U+2069 (FSI, LRI, RLI, PDI) are escaped."""
        # LRI - Left-to-Right Isolate
        assert _sanitize_text("\u2066") == r"\u2066"
        # RLI - Right-to-Left Isolate
        assert _sanitize_text("\u2067") == r"\u2067"
        # FSI - First Strong Isolate
        assert _sanitize_text("\u2068") == r"\u2068"
        # PDI - Pop Directional Isolate
        assert _sanitize_text("\u2069") == r"\u2069"

    def test_sanitize_text_escapes_line_separator(self):
        """Test that U+2028 (Line Separator) is escaped."""
        assert _sanitize_text("\u2028") == r"\u2028"
        assert _sanitize_text("line1\u2028line2") == r"line1\u2028line2"

    def test_sanitize_text_escapes_paragraph_separator(self):
        """Test that U+2029 (Paragraph Separator) is escaped."""
        assert _sanitize_text("\u2029") == r"\u2029"
        assert _sanitize_text("para1\u2029para2") == r"para1\u2029para2"

    def test_sanitize_text_rlo_attack_vector(self):
        """Test the classic RLO attack vector is properly neutralized."""
        # The string "exe\u202etxt\u202c" would display as "txt.exe" without escaping
        malicious = "exe\u202etxt\u202c"
        result = _sanitize_text(malicious)
        # Should NOT contain the raw RLO character
        assert "\u202e" not in result
        # Should contain escaped representation
        assert r"\u202e" in result
        assert r"\u202c" in result

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes bidi control characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        todo = Todo(id=1, text="safe\u202eevil\u202cend", done=False)
        result = TodoFormatter.format_todo(todo)
        # Should contain escaped representations, not raw characters
        assert r"\u202e" in result
        assert r"\u202c" in result
        assert "\u202e" not in result
        assert "\u202c" not in result

    def test_bidi_chars_with_other_controls(self):
        """Test that bidi chars are escaped alongside other control characters."""
        # Mix of ASCII controls, C1 controls, and Unicode bidi
        mixed = "a\x01b\u202ec\x80d"
        result = _sanitize_text(mixed)
        assert result == r"a\x01b\u202ec\x80d"

    def test_valid_unicode_not_affected(self):
        """Test that valid Unicode text (non-control) passes through unchanged."""
        # These should NOT be escaped - they are not bidi controls
        assert _sanitize_text("café") == "café"
        assert _sanitize_text("日本語") == "日本語"
        assert _sanitize_text("🎉") == "🎉"
        # Arabic text (right-to-left naturally) should pass through
        assert _sanitize_text("مرحبا") == "مرحبا"
        # Hebrew text (right-to-left naturally) should pass through
        assert _sanitize_text("שלום") == "שלום"
