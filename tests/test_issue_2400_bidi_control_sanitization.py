"""Tests for Unicode bidirectional control character sanitization (Issue #2400).

Unicode bidirectional control characters (U+202A-U+202E, U+2066-U+2069)
can be used for trojan source attacks where code appears different than
it actually compiles to. These characters must be sanitized to prevent
spoofing attacks.
"""

from flywheel.formatter import _sanitize_text


class TestBidiControlSanitization:
    """Test that bidirectional control characters are properly escaped."""

    def test_sanitize_text_escapes_u202a_lre_left_to_right_embedding(self):
        """Test that U+202A (LRE - Left-to-Right Embedding) is escaped."""
        # LRE character
        assert _sanitize_text("text\u202Aafter") == r"text\u202aafter"

    def test_sanitize_text_escapes_u202b_rle_right_to_left_embedding(self):
        """Test that U+202B (RLE - Right-to-Left Embedding) is escaped."""
        assert _sanitize_text("test\u202Bend") == r"test\u202bend"

    def test_sanitize_text_escapes_u202c_pdf_pop_directional_format(self):
        """Test that U+202C (PDF - Pop Directional Format) is escaped."""
        assert _sanitize_text("start\u202Cstop") == r"start\u202cstop"

    def test_sanitize_text_escapes_u202d_lro_left_to_right_override(self):
        """Test that U+202D (LRO - Left-to-Right Override) is escaped."""
        assert _sanitize_text("before\u202Dafter") == r"before\u202dafter"

    def test_sanitize_text_escapes_u202e_rlo_right_to_left_override(self):
        """Test that U+202E (RLO - Right-to-Left Override) is escaped."""
        assert _sanitize_text("normal\u202Ereversed") == r"normal\u202ereversed"

    def test_sanitize_text_escapes_u2066_lri_left_to_right_isolate(self):
        """Test that U+2066 (LRI - Left-to-Right Isolate) is escaped."""
        assert _sanitize_text("isolated\u2066text") == r"isolated\u2066text"

    def test_sanitize_text_escapes_u2067_rli_right_to_left_isolate(self):
        """Test that U+2067 (RLI - Right-to-Left Isolate) is escaped."""
        assert _sanitize_text("test\u2067end") == r"test\u2067end"

    def test_sanitize_text_escapes_u2068_fsi_first_strong_isolate(self):
        """Test that U+2068 (FSI - First Strong Isolate) is escaped."""
        assert _sanitize_text("first\u2068strong") == r"first\u2068strong"

    def test_sanitize_text_escapes_u2069_pdi_pop_directional_isolate(self):
        """Test that U+2069 (PDI - Pop Directional Isolate) is escaped."""
        assert _sanitize_text("pop\u2069isolate") == r"pop\u2069isolate"

    def test_sanitize_text_normal_unicode_passes_through(self):
        """Test that valid Unicode text is not affected by sanitization."""
        # Arabic (naturally RTL but not a control character)
        assert _sanitize_text("مرحبا") == "مرحبا"
        # Hebrew (naturally RTL but not a control character)
        assert _sanitize_text("שלום") == "שלום"
        # Japanese characters
        assert _sanitize_text("こんにちは") == "こんにちは"
        # Accented characters
        assert _sanitize_text("café") == "café"
        # Emojis
        assert _sanitize_text("🎉") == "🎉"
        # Chinese characters
        assert _sanitize_text("你好") == "你好"

    def test_sanitize_text_mixed_bidi_and_normal(self):
        """Test that bidi controls are escaped in mixed content."""
        # Mix of bidi control chars and normal text
        assert _sanitize_text("normal\u202Abidi\u202Cend") == r"normal\u202abidi\u202cend"
        # Multiple bidi chars
        assert _sanitize_text("start\u202E\u2066\u2069end") == r"start\u202e\u2066\u2069end"

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes bidi control characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        todo = Todo(id=1, text="Buy milk\u202E", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Buy milk\u202e"
