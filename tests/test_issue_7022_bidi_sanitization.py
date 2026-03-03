"""Tests for Unicode bidirectional override character sanitization (Issue #7022).

Unicode bidirectional override characters (U+202A-U+202E, U+2066-U+2069, U+200E-U+200F)
can be used in Trojan Source style attacks to visually reorder text in misleading ways.
These should be escaped to prevent such attacks.
"""

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBidiCharacterSanitization:
    """Test that Unicode bidirectional characters are properly escaped."""

    def test_sanitize_text_escapes_bidi_embedding_chars(self):
        """Test that bidi embedding characters (U+202A-U+202E) are escaped."""
        # LRE - Left-to-Right Embedding (U+202A)
        assert _sanitize_text("Hello\u202aWorld") == r"Hello\u202aWorld"
        # RLE - Right-to-Left Embedding (U+202B)
        assert _sanitize_text("Hello\u202bWorld") == r"Hello\u202bWorld"
        # PDF - Pop Directional Formatting (U+202C)
        assert _sanitize_text("Hello\u202cWorld") == r"Hello\u202cWorld"
        # LRO - Left-to-Right Override (U+202D)
        assert _sanitize_text("Hello\u202dWorld") == r"Hello\u202dWorld"
        # RLO - Right-to-Left Override (U+202E) - critical for Trojan Source attacks
        assert _sanitize_text("Hello\u202eWorld") == r"Hello\u202eWorld"

    def test_sanitize_text_escapes_bidi_isolate_chars(self):
        """Test that bidi isolate characters (U+2066-U+2069) are escaped."""
        # LRI - Left-to-Right Isolate (U+2066)
        assert _sanitize_text("Hello\u2066World") == r"Hello\u2066World"
        # RLI - Right-to-Left Isolate (U+2067)
        assert _sanitize_text("Hello\u2067World") == r"Hello\u2067World"
        # FSI - First Strong Isolate (U+2068)
        assert _sanitize_text("Hello\u2068World") == r"Hello\u2068World"
        # PDI - Pop Directional Isolate (U+2069)
        assert _sanitize_text("Hello\u2069World") == r"Hello\u2069World"

    def test_sanitize_text_escapes_directional_marks(self):
        """Test that directional marks (U+200E-U+200F) are escaped."""
        # LRM - Left-to-Right Mark (U+200E)
        assert _sanitize_text("Hello\u200eWorld") == r"Hello\u200eWorld"
        # RLM - Right-to-Left Mark (U+200F)
        assert _sanitize_text("Hello\u200fWorld") == r"Hello\u200fWorld"

    def test_sanitize_text_trojan_source_attack_prevention(self):
        """Test that Trojan Source style attacks are prevented.

        The RLO character (U+202E) could be used to reverse text display,
        e.g., 'print("Good\u202eelddim.dlrow")' would display as
        'print("Goodworld.middle")' but actually execute with reversed string.
        """
        # A string with RLO that would visually reverse the text
        malicious = "Good\u202eelddim.dlrow"
        sanitized = _sanitize_text(malicious)
        # The sanitized version should NOT contain the raw RLO character
        assert "\u202e" not in sanitized
        # The sanitized version should contain the escaped representation
        assert r"\u202e" in sanitized

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes bidi characters."""
        todo = Todo(id=1, text="Buy\u202emilk", done=False)
        result = TodoFormatter.format_todo(todo)
        # Should not contain raw RLO character
        assert "\u202e" not in result
        # Should contain escaped representation
        assert r"\u202e" in result

    def test_bidi_with_other_controls(self):
        """Test that bidi chars are escaped alongside other control characters."""
        # Mix of bidi, C0, C1, and normal text
        mixed = "a\u202eb\x80c\u2066d"
        sanitized = _sanitize_text(mixed)
        assert sanitized == r"a\u202eb\x80c\u2066d"

    def test_multiple_bidi_chars_in_sequence(self):
        """Test that multiple bidi characters in sequence are all escaped."""
        result = _sanitize_text("\u202a\u202b\u202c\u202d\u202e")
        assert result == r"\u202a\u202b\u202c\u202d\u202e"
