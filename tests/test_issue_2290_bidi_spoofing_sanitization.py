"""Tests for Unicode bidirectional override and zero-width character sanitization (Issue #2290).

Unicode bidirectional override characters (U+202A-U+202E, U+2066-U+2069) and
zero-width characters (U+200B-U+200D, U+FEFF) can be used for text spoofing attacks
where malicious actors hide the true nature of text or reverse the display order.

These should be sanitized to prevent potential spoofing attacks in todo text.
"""

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBidiSpoofingSanitization:
    """Test that Unicode bidirectional override and zero-width characters are properly escaped."""

    # U+202A-U+202E: Bidirectional override characters
    def test_sanitize_text_escapes_left_to_right_override_u202a(self):
        """Test that U+202A Left-to-Right Override is escaped."""
        # U+202A LRO - forces text to display left-to-right
        assert _sanitize_text("test\u202aafter") == r"test\u202aafter"

    def test_sanitize_text_escapes_right_to_left_override_u202b(self):
        """Test that U+202B Right-to-Left Override is escaped."""
        # U+202B RLO - forces text to display right-to-left
        assert _sanitize_text("test\u202bafter") == r"test\u202bafter"

    def test_sanitize_text_escapes_pop_directional_format_u202c(self):
        """Test that U+202C Pop Directional Format is escaped."""
        # U+202B PDF - ends directional override
        assert _sanitize_text("test\u202cafter") == r"test\u202cafter"

    def test_sanitize_text_escapes_left_to_right_embedding_u202d(self):
        """Test that U+202D Left-to-Right Embedding is escaped."""
        # U+202D LRE - marks text as left-to-right
        assert _sanitize_text("test\u202dafter") == r"test\u202dafter"

    def test_sanitize_text_escapes_right_to_left_embedding_u202e(self):
        """Test that U+202E Right-to-Left Embedding is escaped."""
        # U+202E RLE - marks text as right-to-left (commonly used in spoofing)
        assert _sanitize_text("test\u202eafter") == r"test\u202eafter"

    # U+2066-U+2069: Bidirectional isolation characters
    def test_sanitize_text_escapes_left_to_right_isolation_u2066(self):
        """Test that U+2066 Left-to-Right Isolation is escaped."""
        assert _sanitize_text("test\u2066after") == r"test\u2066after"

    def test_sanitize_text_escapes_right_to_left_isolation_u2067(self):
        """Test that U+2067 Right-to-Left Isolation is escaped."""
        assert _sanitize_text("test\u2067after") == r"test\u2067after"

    def test_sanitize_text_escapes_first_strong_isolate_u2068(self):
        """Test that U+2068 First Strong Isolate is escaped."""
        assert _sanitize_text("test\u2068after") == r"test\u2068after"

    def test_sanitize_text_escapes_pop_directional_isolate_u2069(self):
        """Test that U+2069 Pop Directional Isolate is escaped."""
        assert _sanitize_text("test\u2069after") == r"test\u2069after"

    # U+200B-U+200D: Zero-width characters
    def test_sanitize_text_escapes_zero_width_space_u200b(self):
        """Test that U+200B Zero-Width Space is escaped."""
        assert _sanitize_text("test\u200bafter") == r"test\u200bafter"

    def test_sanitize_text_escapes_zero_width_non_joiner_u200c(self):
        """Test that U+200C Zero-Width Non-Joiner is escaped."""
        assert _sanitize_text("test\u200cafter") == r"test\u200cafter"

    def test_sanitize_text_escapes_zero_width_joiner_u200d(self):
        """Test that U+200D Zero-Width Joiner is escaped."""
        assert _sanitize_text("test\u200dafter") == r"test\u200dafter"

    # U+FEFF: Zero-width non-breaking space (BOM)
    def test_sanitize_text_escapes_zero_width_nbsp_ufeff(self):
        """Test that U+FEFF Zero-Width No-Break Space (BOM) is escaped."""
        assert _sanitize_text("test\ufeffafter") == r"test\ufeffafter"

    def test_sanitize_text_handles_multiple_spoofing_chars(self):
        """Test that multiple bidirectional/zero-width characters are all escaped."""
        # Mix of RLO, zero-width space, and LRE
        assert _sanitize_text("a\u202eb\u200bc\u202ad") == r"a\u202eb\u200bc\u202ad"

    def test_legitimate_arabic_text_not_affected(self):
        """Test that legitimate Arabic text still displays correctly.

        This is important - we only want to escape the control characters
        that override direction, not the actual Arabic script.
        """
        # Arabic text for "Hello" (مرحبا)
        assert _sanitize_text("مرحبا") == "مرحبا"
        # Arabic with numbers
        assert _sanitize_text("العربية 123") == "العربية 123"

    def test_legitimate_hebrew_text_not_affected(self):
        """Test that legitimate Hebrew text still displays correctly."""
        # Hebrew text for "Shalom" (שלום)
        assert _sanitize_text("שלום") == "שלום"
        # Hebrew with English mix
        assert _sanitize_text("Hello שלום") == "Hello שלום"

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes bidirectional characters."""
        todo = Todo(id=1, text="Buy milk\u202e", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Buy milk\u202e"

    def test_format_todo_escapes_zero_width_chars(self):
        """Test that format_todo properly escapes zero-width characters."""
        todo = Todo(id=1, text="Buy milk\u200b", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Buy milk\u200b"
