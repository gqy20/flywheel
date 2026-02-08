"""Tests for Unicode bidirectional override and zero-width character sanitization (Issue #2290).

Unicode bidirectional override characters (U+202A-U+202E, U+2066-U+2069) and
zero-width characters (U+200B-U+200D, U+FEFF) can be used for text spoofing attacks
where malicious actors hide phishing URLs or reverse text to deceive users.

These characters should be sanitized to prevent such attacks.
"""

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBidiAndZeroWidthSanitization:
    """Test that bidi override and zero-width characters are properly escaped."""

    def test_sanitize_text_escapes_right_to_left_override_u202e(self):
        """Test that U+202E (Right-to-Left Override) is escaped."""
        # U+202E = 0x202E = 8238 in decimal
        # This character can reverse text for spoofing attacks
        assert _sanitize_text("test\u202Eafter") == r"test\u202eafter"

    def test_sanitize_text_escapes_left_to_right_override_u202d(self):
        """Test that U+202D (Left-to-Right Override) is escaped."""
        # U+202D = 0x202D = 8237 in decimal
        assert _sanitize_text("test\u202Dafter") == r"test\u202dafter"

    def test_sanitize_text_escapes_all_bidi_override_chars(self):
        """Test that all bidi override characters (U+202A-U+202E) are escaped."""
        # U+202A: Left-to-Right Embedding
        assert _sanitize_text("start\u202Aend") == r"start\u202aend"
        # U+202B: Right-to-Left Embedding
        assert _sanitize_text("start\u202Bend") == r"start\u202bend"
        # U+202C: Pop Directional Formatting
        assert _sanitize_text("start\u202Cend") == r"start\u202cend"
        # U+202D: Left-to-Right Override
        assert _sanitize_text("start\u202Dend") == r"start\u202dend"
        # U+202E: Right-to-Left Override
        assert _sanitize_text("start\u202Eend") == r"start\u202eend"

    def test_sanitize_text_escapes_isolate_controls_u2066_to_u2069(self):
        """Test that bidi isolate controls (U+2066-U+2069) are escaped."""
        # U+2066: Left-to-Right Isolate
        assert _sanitize_text("start\u2066end") == r"start\u2066end"
        # U+2067: Right-to-Left Isolate
        assert _sanitize_text("start\u2067end") == r"start\u2067end"
        # U+2068: First Strong Isolate
        assert _sanitize_text("start\u2068end") == r"start\u2068end"
        # U+2069: Pop Directional Isolate
        assert _sanitize_text("start\u2069end") == r"start\u2069end"

    def test_sanitize_text_escapes_zero_width_space_u200b(self):
        """Test that U+200B (Zero-Width Space) is escaped."""
        # U+200B = 0x200B = 8203 in decimal
        assert _sanitize_text("test\u200Bafter") == r"test\u200bafter"

    def test_sanitize_text_escapes_zero_width_non_joiner_u200c(self):
        """Test that U+200C (Zero-Width Non-Joiner) is escaped."""
        # U+200C = 0x200C = 8204 in decimal
        assert _sanitize_text("test\u200Cafter") == r"test\u200cafter"

    def test_sanitize_text_escapes_zero_width_joiner_u200d(self):
        """Test that U+200D (Zero-Width Joiner) is escaped."""
        # U+200D = 0x200D = 8205 in decimal
        assert _sanitize_text("test\u200Dafter") == r"test\u200dafter"

    def test_sanitize_text_escapes_zero_width_no_break_space_ufeff(self):
        """Test that U+FEFF (Zero-Width No-Break Space / BOM) is escaped."""
        # U+FEFF = 0xFEFF = 65279 in decimal
        assert _sanitize_text("test\uFEFFafter") == r"test\ufeffafter"

    def test_sanitize_text_mixed_spoofing_chars(self):
        """Test that mixed bidi and zero-width characters are all escaped."""
        # Simulate a potential spoofing attack
        # "paypal.com" with RLO to hide ".evil" before it
        # evil.moc\u202Elapyap (renders as paypal.com evil. in RTL context)
        malicious = "evil.moc\u202Elapyap"
        result = _sanitize_text(malicious)
        assert result == r"evil.moc\u202elapyap"

    def test_sanitize_text_preserves_legitimate_arabic_and_hebrew(self):
        """Test that legitimate Arabic and Hebrew text still displays correctly."""
        # Arabic text
        assert _sanitize_text("مرحبا") == "مرحبا"
        # Hebrew text
        assert _sanitize_text("שלום") == "שלום"
        # These should pass through as they are NOT bidi control chars

    def test_sanitize_text_preserves_other_legitimate_unicode(self):
        """Test that other legitimate Unicode is not affected."""
        # Emojis
        assert _sanitize_text("🎉") == "🎉"
        # CJK
        assert _sanitize_text("你好") == "你好"
        # Accented characters
        assert _sanitize_text("café") == "café"

    def test_format_todo_escapes_bidi_and_zero_width_chars(self):
        """Test that format_todo properly escapes bidi and zero-width characters."""
        todo = Todo(id=1, text="Buy milk\u202Eevil", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Buy milk\u202eevil"
