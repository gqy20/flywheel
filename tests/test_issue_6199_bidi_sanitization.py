"""Tests for BiDi (Bidirectional) character sanitization (Issue #6199).

BiDi override characters (U+202A-U+202E, U+2066-U+2069) can make text
display backwards or change direction, enabling visual spoofing attacks.
For example, 'exe.pac' with a RLO character can appear as 'cap.exe'.

These tests ensure BiDi characters are escaped to visible representations
to prevent text direction spoofing attacks.
"""

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBiDiSanitization:
    """Test that BiDi override characters are properly escaped."""

    def test_sanitize_text_escapes_right_to_left_override_u202e(self):
        """Test that U+202E (RLO - Right-to-Left Override) is escaped."""
        # U+202E makes text display right-to-left
        # 'exe.pac' with RLO would display as 'cap.exe'
        result = _sanitize_text("\u202eexe.pac")
        assert "\u202e" not in result
        assert "\\u202e" in result

    def test_sanitize_text_escapes_all_bidi_directional_chars(self):
        """Test that all directional formatting characters are escaped."""
        # U+202A - LRE (Left-to-Right Embedding)
        assert _sanitize_text("\u202atext") == "\\u202atext"
        # U+202B - RLE (Right-to-Left Embedding)
        assert _sanitize_text("\u202btext") == "\\u202btext"
        # U+202C - PDF (Pop Directional Format)
        assert _sanitize_text("\u202ctext") == "\\u202ctext"
        # U+202D - LRO (Left-to-Right Override)
        assert _sanitize_text("\u202dtext") == "\\u202dtext"
        # U+202E - RLO (Right-to-Left Override)
        assert _sanitize_text("\u202etext") == "\\u202etext"

    def test_sanitize_text_escapes_bidi_isolate_chars(self):
        """Test that BiDi isolate characters (U+2066-U+2069) are escaped."""
        # U+2066 - LRI (Left-to-Right Isolate)
        assert _sanitize_text("\u2066text") == "\\u2066text"
        # U+2067 - RLI (Right-to-Left Isolate)
        assert _sanitize_text("\u2067text") == "\\u2067text"
        # U+2068 - FSI (First Strong Isolate)
        assert _sanitize_text("\u2068text") == "\\u2068text"
        # U+2069 - PDI (Pop Directional Isolate)
        assert _sanitize_text("\u2069text") == "\\u2069text"

    def test_sanitize_text_bidi_distinguishes_from_literal(self):
        """Test that actual BiDi char produces different output than literal text."""
        actual_bidi = _sanitize_text("\u202e")  # Actual U+202E character
        literal_text = _sanitize_text("\\u202e")  # Literal backslash-u-202e
        # These should produce different outputs
        assert actual_bidi != literal_text
        # Actual BiDi should be escaped
        assert "\\u202e" in actual_bidi
        # Literal should have escaped backslash
        assert "\\\\u202e" in literal_text

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes BiDi characters."""
        # Create a todo with RLO character that would spoof 'cap.exe'
        todo = Todo(id=1, text="\u202eexe.pac", done=False)
        result = TodoFormatter.format_todo(todo)
        # Should not contain raw BiDi character
        assert "\u202e" not in result
        # Should contain escaped representation
        assert "\\u202e" in result

    def test_format_todo_with_multiple_bidi_chars(self):
        """Test that multiple BiDi characters are all escaped."""
        todo = Todo(id=1, text="\u202a\u202b\u202e\u2066text", done=False)
        result = TodoFormatter.format_todo(todo)
        assert "\u202a" not in result
        assert "\u202b" not in result
        assert "\u202e" not in result
        assert "\u2066" not in result
        assert "\\u202a" in result
        assert "\\u202b" in result
        assert "\\u202e" in result
        assert "\\u2066" in result

    def test_sanitize_text_bidi_with_other_controls(self):
        """Test that BiDi chars are escaped alongside other control characters."""
        # Mix of BiDi, C0 controls, and normal text
        result = _sanitize_text("a\u202eb\x01c")
        assert "\\u202e" in result
        assert "\\x01" in result
        assert "\u202e" not in result
        assert "\x01" not in result

    def test_sanitize_text_normal_unicode_passes_through(self):
        """Test that normal Unicode (non-BiDi) passes through unchanged."""
        # These should NOT be escaped - they're safe characters
        assert _sanitize_text("café") == "café"
        assert _sanitize_text("日本語") == "日本語"
        assert _sanitize_text("emoji 🎉") == "emoji 🎉"
