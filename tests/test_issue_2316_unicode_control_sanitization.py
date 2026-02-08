"""Tests for Unicode bidirectional override character sanitization (Issue #2316).

Unicode bidirectional override characters (U+202A-U+202E) and zero-width
characters (U+200B-U+200D) can be used for text spoofing attacks where
malicious users can make text appear different than it actually is.
For example, an attacker could use RTL override to make a file extension
appear as .txt when it's actually .exe.

These characters should be escaped to prevent terminal output manipulation.
"""

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestUnicodeBidirectionalOverrideSanitization:
    """Test that Unicode bidirectional override characters are properly escaped."""

    def test_sanitize_text_escapes_rtl_override_u202e(self):
        """Test that Right-to-Left Override (U+202E) is escaped."""
        # U+202E = RIGHT-TO-LEFT OVERRIDE
        # This forces following text to be rendered right-to-left
        assert _sanitize_text("test\u202eafter") == r"test\u202eafter"
        assert _sanitize_text("file.txt\u202eexe") == r"file.txt\u202eexe"

    def test_sanitize_text_escapes_ltr_override_u202a(self):
        """Test that Left-to-Right Override (U+202A) is escaped."""
        # U+202A = LEFT-TO-RIGHT OVERRIDE
        assert _sanitize_text("test\u202aafter") == r"test\u202aafter"

    def test_sanitize_text_escapes_zero_width_space_u200b(self):
        """Test that Zero Width Space (U+200B) is escaped."""
        # U+200B = ZERO WIDTH SPACE
        # Invisible character that can break word rendering
        assert _sanitize_text("test\u200bafter") == r"test\u200bafter"

    def test_sanitize_text_escapes_zero_width_non_joiner_u200c(self):
        """Test that Zero Width Non-Joiner (U+200C) is escaped."""
        # U+200C = ZERO WIDTH NON-JOINER
        assert _sanitize_text("test\u200cafter") == r"test\u200cafter"

    def test_sanitize_text_escapes_zero_width_joiner_u200d(self):
        """Test that Zero Width Joiner (U+200D) is escaped."""
        # U+200D = ZERO WIDTH JOINER
        assert _sanitize_text("test\u200dafter") == r"test\u200dafter"

    def test_sanitize_text_escapes_all_bidirectional_overrides(self):
        """Test all bidirectional override characters in range U+202A-U+202E."""
        # U+202A = LEFT-TO-RIGHT OVERRIDE
        # U+202B = RIGHT-TO-LEFT OVERRIDE
        # U+202C = POP DIRECTIONAL FORMAT
        # U+202D = LEFT-TO-RIGHT EMBEDDING
        # U+202E = RIGHT-TO-LEFT EMBEDDING
        assert _sanitize_text("\u202a") == r"\u202a"
        assert _sanitize_text("\u202b") == r"\u202b"
        assert _sanitize_text("\u202c") == r"\u202c"
        assert _sanitize_text("\u202d") == r"\u202d"
        assert _sanitize_text("\u202e") == r"\u202e"

    def test_sanitize_text_escapes_zero_width_chars_in_range(self):
        """Test all zero-width characters in range U+200B-U+200D."""
        # U+200B = ZERO WIDTH SPACE
        # U+200C = ZERO WIDTH NON-JOINER
        # U+200D = ZERO WIDTH JOINER
        assert _sanitize_text("\u200b") == r"\u200b"
        assert _sanitize_text("\u200c") == r"\u200c"
        assert _sanitize_text("\u200d") == r"\u200d"

    def test_sanitize_text_does_not_escape_normal_arabic_text(self):
        """Test that normal Arabic text is NOT escaped.

        Arabic is a naturally right-to-left language and should display
        correctly without needing any override characters.
        """
        # Arabic text: "Hello" in Arabic
        arabic_text = "مرحبا"
        assert _sanitize_text(arabic_text) == arabic_text

        # Arabic numbers
        assert _sanitize_text("٠١٢٣٤٥٦٧٨٩") == "٠١٢٣٤٥٦٧٨٩"

    def test_sanitize_text_does_not_escape_normal_hebrew_text(self):
        """Test that normal Hebrew text is NOT escaped.

        Hebrew is a naturally right-to-left language and should display
        correctly without needing any override characters.
        """
        # Hebrew text: "Shalom" (peace/greeting)
        hebrew_text = "שלום"
        assert _sanitize_text(hebrew_text) == hebrew_text

    def test_sanitize_text_mixed_unicode_with_control_chars(self):
        """Test sanitization of text with mixed Unicode and control characters."""
        # Normal text with embedded RTL override
        assert _sanitize_text("normal\u202e") == r"normal\u202e"
        # Arabic text with embedded zero-width space (should escape the ZWS only)
        assert _sanitize_text("مرحبا\u200b") == r"مرحبا\u200b"

    def test_format_todo_escapes_unicode_control_chars(self):
        """Test that format_todo properly escapes Unicode bidirectional overrides."""
        todo = Todo(id=1, text="Buy milk\u202eexe", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Buy milk\u202eexe"

    def test_format_todo_with_zero_width_space(self):
        """Test that format_todo properly escapes zero-width characters."""
        todo = Todo(id=2, text="Task\u200bname", done=True)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[x]   2 Task\u200bname"

    def test_sanitize_text_with_multiple_control_chars(self):
        """Test text containing multiple Unicode control characters."""
        # Multiple bidirectional overrides
        assert _sanitize_text("\u202a\u202b\u202c") == r"\u202a\u202b\u202c"
        # Multiple zero-width characters
        assert _sanitize_text("\u200b\u200c\u200d") == r"\u200b\u200c\u200d"
        # Mix of both types
        assert _sanitize_text("a\u202eb\u200bc") == r"a\u202eb\u200bc"
