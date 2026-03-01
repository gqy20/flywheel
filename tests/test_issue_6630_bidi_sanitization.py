"""Tests for Unicode bidirectional override character sanitization (Issue #6630).

Unicode bidirectional override characters can be used for display spoofing attacks
by reversing or manipulating text direction. These characters should be escaped
to prevent security issues.

Bidirectional characters to sanitize:
- U+202A-U+202E: Bidirectional formatting (LRE, RLE, PDF, LRO, RLO)
- U+2066-U+2069: Bidirectional isolate controls (LRI, RLI, FSI, PDI)
- U+200E-U+200F: Left-to-right and right-to-left marks (LRM, RLM)
- U+FEFF: Byte order mark / Zero-width no-break space
"""

from flywheel.formatter import _sanitize_text


class TestBidiCharacterSanitization:
    """Test that Unicode bidirectional override characters are properly escaped."""

    def test_sanitize_text_escapes_rtl_override_u202e(self):
        """Test that U+202E (RTL Override) is escaped - classic spoofing attack vector."""
        # U+202E reverses text display, enabling spoofing like "exe.html" appearing as "elpmiS.exe"
        assert _sanitize_text("Hello\u202eWorld") == r"Hello\u202eWorld"
        assert _sanitize_text("\u202e") == r"\u202e"

    def test_sanitize_text_escapes_all_bidi_formatting_chars(self):
        """Test all bidirectional formatting characters (U+202A-U+202E)."""
        # U+202A: Left-to-Right Embedding (LRE)
        assert _sanitize_text("\u202a") == r"\u202a"
        # U+202B: Right-to-Left Embedding (RLE)
        assert _sanitize_text("\u202b") == r"\u202b"
        # U+202C: Pop Directional Formatting (PDF)
        assert _sanitize_text("\u202c") == r"\u202c"
        # U+202D: Left-to-Right Override (LRO)
        assert _sanitize_text("\u202d") == r"\u202d"
        # U+202E: Right-to-Left Override (RLO)
        assert _sanitize_text("\u202e") == r"\u202e"

    def test_sanitize_text_escapes_bidi_isolate_controls(self):
        """Test bidirectional isolate controls (U+2066-U+2069)."""
        # U+2066: Left-to-Right Isolate (LRI)
        assert _sanitize_text("\u2066") == r"\u2066"
        # U+2067: Right-to-Left Isolate (RLI)
        assert _sanitize_text("\u2067") == r"\u2067"
        # U+2068: First Strong Isolate (FSI)
        assert _sanitize_text("\u2068") == r"\u2068"
        # U+2069: Pop Directional Isolate (PDI)
        assert _sanitize_text("\u2069") == r"\u2069"

    def test_sanitize_text_escapes_direction_marks(self):
        """Test left-to-right and right-to-left marks (U+200E-U+200F)."""
        # U+200E: Left-to-Right Mark (LRM)
        assert _sanitize_text("\u200e") == r"\u200e"
        # U+200F: Right-to-Left Mark (RLM)
        assert _sanitize_text("\u200f") == r"\u200f"

    def test_sanitize_text_escapes_bom(self):
        """Test that BOM/zero-width no-break space (U+FEFF) is escaped."""
        assert _sanitize_text("\ufeff") == r"\ufeff"
        assert _sanitize_text("text\ufeffmore") == r"text\ufeffmore"

    def test_format_todo_escapes_bidi_spoofing_pattern(self):
        """Test that format_todo properly escapes bidi spoofing attack patterns."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        # Simulated attack: using RTL override to make "exe.html" appear as "elpmiS.exe"
        malicious_text = "Readme\u202eelpmiS.exe"
        todo = Todo(id=1, text=malicious_text, done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Readme\u202eelpmiS.exe"

    def test_unicode_text_passes_through_unchanged(self):
        """Test that valid Unicode text is not affected by sanitization."""
        # Japanese characters
        assert _sanitize_text("こんにちは") == "こんにちは"
        # Accented characters
        assert _sanitize_text("café") == "café"
        # Emojis
        assert _sanitize_text("🎉") == "🎉"
        # Chinese characters
        assert _sanitize_text("你好") == "你好"
        # Arabic (natural RTL, not override chars)
        assert _sanitize_text("مرحبا") == "مرحبا"
        # Hebrew (natural RTL, not override chars)
        assert _sanitize_text("שלום") == "שלום"

    def test_bidi_chars_with_other_controls(self):
        """Test that bidi chars are escaped alongside other control characters."""
        # Mix of bidi override and C1 control
        assert _sanitize_text("\u202e\x80") == r"\u202e\x80"
        # Mix of bidi and C0 control
        assert _sanitize_text("\u200e\x01") == r"\u200e\x01"
