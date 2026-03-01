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
        """Test that RTL Override (U+202E) is escaped to prevent display spoofing."""
        # U+202E is the Right-to-Left Override character
        # This could be used to display "exe.txt" as "txt.exe"
        result = _sanitize_text("test\u202efile")
        assert "\u202e" not in result
        assert "\\u202e" in result.lower() or "\\x" in result

    def test_sanitize_text_escapes_ltr_override_u202d(self):
        """Test that LTR Override (U+202D) is escaped."""
        result = _sanitize_text("test\u202dfile")
        assert "\u202d" not in result

    def test_sanitize_text_escapes_bidi_embedding_chars(self):
        """Test that bidirectional embedding characters (U+202A-U+202B) are escaped."""
        # LRE - Left-to-Right Embedding
        result = _sanitize_text("text\u202aend")
        assert "\u202a" not in result
        # RLE - Right-to-Left Embedding
        result = _sanitize_text("text\u202bend")
        assert "\u202b" not in result

    def test_sanitize_text_escapes_bidi_isolate_chars(self):
        """Test that bidirectional isolate characters (U+2066-U+2069) are escaped."""
        # FSI - First Strong Isolate
        result = _sanitize_text("text\u2068end")
        assert "\u2068" not in result
        # PDI - Pop Directional Isolate
        result = _sanitize_text("text\u2069end")
        assert "\u2069" not in result
        # LRI - Left-to-Right Isolate
        result = _sanitize_text("text\u2066end")
        assert "\u2066" not in result
        # RLI - Right-to-Left Isolate
        result = _sanitize_text("text\u2067end")
        assert "\u2067" not in result

    def test_sanitize_text_escapes_directional_markers(self):
        """Test that directional markers (U+200E-U+200F) are escaped."""
        # LRM - Left-to-Right Mark
        result = _sanitize_text("text\u200eend")
        assert "\u200e" not in result
        # RLM - Right-to-Left Mark
        result = _sanitize_text("text\u200fend")
        assert "\u200f" not in result

    def test_sanitize_text_escapes_bom_ufeff(self):
        """Test that BOM/Zero Width No-Break Space (U+FEFF) is escaped."""
        # BOM can be used to hide content at the start of files
        result = _sanitize_text("\ufeffhidden")
        assert "\ufeff" not in result

    def test_sanitize_text_escapes_pdf_u202c(self):
        """Test that Pop Directional Formatting (U+202C) is escaped."""
        result = _sanitize_text("text\u202cend")
        assert "\u202c" not in result

    def test_format_todo_with_bidi_spoofing_attack(self):
        """Test that format_todo properly escapes bidi spoofing patterns.

        A classic attack: displaying "exe.txt" when the actual name is "txt.exe"
        by using RTL override character.
        """
        # "txt\u202eexe." would display as "txt.exe" but is actually "txt.exe" reversed
        malicious_text = "readme\u202etxt.exe"
        todo = Todo(id=1, text=malicious_text, done=False)
        result = TodoFormatter.format_todo(todo)
        # The bidi character should be escaped, not present as-is
        assert "\u202e" not in result

    def test_normal_unicode_passes_through(self):
        """Test that normal Unicode (emoji, CJK, accented) passes through unchanged."""
        # Emojis
        assert _sanitize_text("🎉 Party!") == "🎉 Party!"
        # CJK
        assert _sanitize_text("日本語") == "日本語"
        # Accented
        assert _sanitize_text("café résumé") == "café résumé"
        # Mixed normal Unicode
        assert _sanitize_text("Hello 世界 🌍") == "Hello 世界 🌍"

    def test_bidi_with_other_control_chars(self):
        """Test that bidi chars are escaped alongside other control characters."""
        # Mix of bidi override and C0 control
        result = _sanitize_text("a\u202e\x01b")
        assert "\u202e" not in result
        assert "\x01" not in result
