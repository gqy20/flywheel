"""Tests for Unicode bidirectional override character sanitization (Issue #6630).

Unicode bidirectional override characters (U+202A-U+202E, U+2066-U+2069,
U+200E-U+200F, U+FEFF) can be used for display spoofing attacks where
text appears different than its actual content. These should be escaped
to prevent security issues.
"""

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBidiCharacterSanitization:
    """Test that Unicode bidirectional override characters are properly escaped."""

    def test_sanitize_text_escapes_rtl_override_u202e(self):
        """Test that RTL Override (U+202E) is escaped."""
        # U+202E is the Right-to-Left Override character
        # This can be used to make "exe.py" appear as "yp.exe"
        assert _sanitize_text("test\u202eafter") == r"test\u202eafter"

    def test_sanitize_text_escapes_ltr_override_u202d(self):
        """Test that LTR Override (U+202D) is escaped."""
        # U+202D is the Left-to-Right Override character
        assert _sanitize_text("test\u202dafter") == r"test\u202dafter"

    def test_sanitize_text_escapes_bidi_embedding_chars(self):
        """Test bidirectional embedding characters (U+202A-U+202B)."""
        # U+202A: Left-to-Right Embedding
        assert _sanitize_text("text\u202aend") == r"text\u202aend"
        # U+202B: Right-to-Left Embedding
        assert _sanitize_text("text\u202bend") == r"text\u202bend"

    def test_sanitize_text_escapes_bidi_isolate_chars(self):
        """Test bidirectional isolate characters (U+2066-U+2069)."""
        # U+2066: Left-to-Right Isolate
        assert _sanitize_text("text\u2066end") == r"text\u2066end"
        # U+2067: Right-to-Left Isolate
        assert _sanitize_text("text\u2067end") == r"text\u2067end"
        # U+2068: First Strong Isolate
        assert _sanitize_text("text\u2068end") == r"text\u2068end"
        # U+2069: Pop Directional Isolate
        assert _sanitize_text("text\u2069end") == r"text\u2069end"

    def test_sanitize_text_escapes_directional_marks(self):
        """Test directional marks (U+200E-U+200F)."""
        # U+200E: Left-to-Right Mark
        assert _sanitize_text("text\u200eend") == r"text\u200eend"
        # U+200F: Right-to-Left Mark
        assert _sanitize_text("text\u200fend") == r"text\u200fend"

    def test_sanitize_text_escapes_bom_ufeff(self):
        """Test that BOM/Zero Width No-Break Space (U+FEFF) is escaped."""
        # U+FEFF can be used as an invisible character at the start of text
        assert _sanitize_text("test\ufeffafter") == r"test\ufeffafter"

    def test_sanitize_text_escapes_pop_directional_formatting_u202c(self):
        """Test Pop Directional Formatting (U+202C)."""
        assert _sanitize_text("text\u202cend") == r"text\u202cend"

    def test_format_todo_escapes_bidi_spoofing_attack(self):
        """Test that format_todo properly escapes bidirectional spoofing patterns."""
        # Simulate a spoofing attack: "safe.exe" could appear as "exe.efas" with RTL
        todo = Todo(id=1, text="safe\u202eexe.py", done=False)
        result = TodoFormatter.format_todo(todo)
        # The bidi character should be escaped, not rendered
        assert "\u202e" not in result
        assert r"\u202e" in result

    def test_bidi_with_normal_unicode_unchanged(self):
        """Test that normal Unicode text still passes through unchanged."""
        # Emojis should still work
        assert _sanitize_text("Hello 🎉") == "Hello 🎉"
        # CJK characters should still work
        assert _sanitize_text("日本語") == "日本語"
        # Accented characters should still work
        assert _sanitize_text("café") == "café"

    def test_mixed_bidi_and_control_chars(self):
        """Test that bidi chars are escaped alongside other control characters."""
        # Mix of bidi (U+202E) and C0 control (0x01)
        assert _sanitize_text("a\u202eb\x01c") == r"a\u202eb\x01c"

    def test_multiple_bidi_chars_in_sequence(self):
        """Test multiple bidi characters in sequence."""
        # Multiple bidi override chars
        assert _sanitize_text("\u202e\u202d\u2066") == r"\u202e\u202d\u2066"
