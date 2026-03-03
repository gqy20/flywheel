"""Tests for Unicode bidirectional character sanitization (Issue #7022).

Unicode bidirectional override characters (U+202A-U+202E, U+2066-U+2069, U+200E-U+200F)
can be used in Trojan Source style attacks to hide malicious code by reversing
or changing the display direction of text. These should be sanitized to prevent
such attacks.
"""

from flywheel.formatter import _sanitize_text


class TestBidiCharacterSanitization:
    """Test that Unicode bidirectional characters are properly escaped."""

    def test_sanitize_text_escapes_bidi_embedding_chars_u202a_to_u202e(self):
        """Test that bidi embedding/override characters (U+202A-U+202E) are escaped."""
        # U+202A LEFT-TO-RIGHT EMBEDDING
        assert _sanitize_text("text\u202aafter") == r"text\u202aafter"
        # U+202B RIGHT-TO-LEFT EMBEDDING
        assert _sanitize_text("text\u202bafter") == r"text\u202bafter"
        # U+202C POP DIRECTIONAL FORMATTING
        assert _sanitize_text("text\u202cafter") == r"text\u202cafter"
        # U+202D LEFT-TO-RIGHT OVERRIDE
        assert _sanitize_text("text\u202dafter") == r"text\u202dafter"
        # U+202E RIGHT-TO-LEFT OVERRIDE (RLO) - the most dangerous one
        assert _sanitize_text("text\u202eafter") == r"text\u202eafter"

    def test_sanitize_text_escapes_bidi_isolate_chars_u2066_to_u2069(self):
        """Test that bidi isolate characters (U+2066-U+2069) are escaped."""
        # U+2066 LEFT-TO-RIGHT ISOLATE
        assert _sanitize_text("text\u2066after") == r"text\u2066after"
        # U+2067 RIGHT-TO-LEFT ISOLATE
        assert _sanitize_text("text\u2067after") == r"text\u2067after"
        # U+2068 FIRST STRONG ISOLATE
        assert _sanitize_text("text\u2068after") == r"text\u2068after"
        # U+2069 POP DIRECTIONAL ISOLATE
        assert _sanitize_text("text\u2069after") == r"text\u2069after"

    def test_sanitize_text_escapes_bidi_marks_u200e_u200f(self):
        """Test that LRM/RLM marks (U+200E-U+200F) are escaped."""
        # U+200E LEFT-TO-RIGHT MARK
        assert _sanitize_text("text\u200eafter") == r"text\u200eafter"
        # U+200F RIGHT-TO-LEFT MARK
        assert _sanitize_text("text\u200fafter") == r"text\u200fafter"

    def test_sanitize_text_prevents_trojan_source_attack(self):
        """Test that a Trojan Source style attack is prevented.

        The RLO character (U+202E) can be used to display text in reverse,
        potentially hiding malicious code. For example, 'Hello\u202eWorld'
        would display as 'HellodlroW' without sanitization.
        """
        # RLO attack example
        malicious = "Hello\u202eWorld"
        result = _sanitize_text(malicious)
        # The bidi character should be escaped, not passed through
        assert "\u202e" not in result
        assert r"\u202e" in result
        assert result == r"Hello\u202eWorld"

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes bidi characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        todo = Todo(id=1, text="Buy milk\u202e", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Buy milk\u202e"
        # Verify no raw bidi character in output
        assert "\u202e" not in result

    def test_bidi_chars_with_other_controls(self):
        """Test that bidi chars are escaped alongside other control characters."""
        # Mix of C0, C1, and bidi chars
        assert _sanitize_text("a\u202eb\x80c") == r"a\u202eb\x80c"
        # Mix of multiple bidi chars
        assert _sanitize_text("\u202a\u2066\u200e") == r"\u202a\u2066\u200e"

    def test_unicode_text_without_bidi_passes_through(self):
        """Test that normal Unicode text without bidi chars passes through unchanged."""
        # Japanese characters
        assert _sanitize_text("こんにちは") == "こんにちは"
        # Arabic text (naturally RTL, but no bidi override chars)
        assert _sanitize_text("مرحبا") == "مرحبا"
        # Hebrew text (naturally RTL, but no bidi override chars)
        assert _sanitize_text("שלום") == "שלום"
        # Emojis
        assert _sanitize_text("🎉🚀✨") == "🎉🚀✨"
