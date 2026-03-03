"""Tests for Unicode bidirectional character sanitization (Issue #7022).

Unicode bidirectional override characters can be used for "Trojan Source"
attacks where text appears differently when rendered vs when viewed in code.
These characters should be escaped to prevent such attacks.

Reference: https://trojansource.codes/
"""

from flywheel.formatter import _sanitize_text


class TestBidirectionalCharacterSanitization:
    """Test that Unicode bidirectional characters are properly escaped."""

    def test_sanitize_text_escapes_bidi_embedding_chars_u202a_to_u202e(self):
        """Test that bidi embedding/override chars (U+202A-U+202E) are escaped."""
        # LRE - Left-to-Right Embedding (U+202A)
        assert _sanitize_text("Hello\u202aWorld") == r"Hello\u202aWorld"
        # RLE - Right-to-Left Embedding (U+202B)
        assert _sanitize_text("Hello\u202bWorld") == r"Hello\u202bWorld"
        # PDF - Pop Directional Formatting (U+202C)
        assert _sanitize_text("Hello\u202cWorld") == r"Hello\u202cWorld"
        # LRO - Left-to-Right Override (U+202D)
        assert _sanitize_text("Hello\u202dWorld") == r"Hello\u202dWorld"
        # RLO - Right-to-Left Override (U+202E) - the most dangerous one
        assert _sanitize_text("Hello\u202eWorld") == r"Hello\u202eWorld"

    def test_sanitize_text_escapes_bidi_isolate_chars_u2066_to_u2069(self):
        """Test that bidi isolate chars (U+2066-U+2069) are escaped."""
        # LRI - Left-to-Right Isolate (U+2066)
        assert _sanitize_text("Hello\u2066World") == r"Hello\u2066World"
        # RLI - Right-to-Left Isolate (U+2067)
        assert _sanitize_text("Hello\u2067World") == r"Hello\u2067World"
        # FSI - First Strong Isolate (U+2068)
        assert _sanitize_text("Hello\u2068World") == r"Hello\u2068World"
        # PDI - Pop Directional Isolate (U+2069)
        assert _sanitize_text("Hello\u2069World") == r"Hello\u2069World"

    def test_sanitize_text_escapes_bidi_marks_u200e_u200f(self):
        """Test that LRM/RLM marks (U+200E, U+200F) are escaped."""
        # LRM - Left-to-Right Mark (U+200E)
        assert _sanitize_text("Hello\u200eWorld") == r"Hello\u200eWorld"
        # RLM - Right-to-Left Mark (U+200F)
        assert _sanitize_text("Hello\u200fWorld") == r"Hello\u200fWorld"

    def test_sanitize_text_escapes_trojan_source_example(self):
        """Test a realistic Trojan Source attack pattern.

        Example: A todo with RLO could make "Delete all files" appear as
        "selif lla etelD" when rendered, hiding malicious intent.
        """
        # RLO (U+202E) reverses display of following text
        malicious = "Access granted\u202e\u0031\u0032\u0033"
        result = _sanitize_text(malicious)
        # The bidi char should be escaped, not passed through
        assert "\\u202e" in result
        assert "\u202e" not in result

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes bidi characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        # Create todo with RLO character
        todo = Todo(id=1, text="Normal text\u202eReversed", done=False)
        result = TodoFormatter.format_todo(todo)
        # The bidi char should be escaped
        assert r"\u202e" in result
        assert "\u202e" not in result

    def test_bidi_chars_with_other_controls(self):
        """Test that bidi chars are escaped alongside other control characters."""
        # Mix of bidi (U+202E), C0 (0x01), and C1 (0x80)
        result = _sanitize_text("a\u202eb\x80c")
        assert result == r"a\u202eb\x80c"

    def test_unicode_text_without_bidi_passes_through(self):
        """Test that normal Unicode text (without bidi) is not affected."""
        # Japanese, Chinese, emojis should still work
        assert _sanitize_text("こんにちは") == "こんにちは"
        assert _sanitize_text("你好") == "你好"
        assert _sanitize_text("🎉") == "🎉"
        # Arabic/Hebrew text should pass through (it's legit RTL, not bidi override)
        assert _sanitize_text("مرحبا") == "مرحبا"
        assert _sanitize_text("שלום") == "שלום"
