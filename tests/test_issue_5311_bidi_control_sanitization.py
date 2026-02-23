"""Tests for Unicode Bidi control character sanitization (Issue #5311).

Unicode Bidi (bidirectional) control characters can be abused to display
text differently than its actual content, enabling text spoofing attacks.
These characters should be sanitized to prevent terminal output manipulation.

Bidi control character ranges:
- U+200E-U+200F: LRM/RLM (Left-to-Right/Right-to-Left Mark)
- U+202A-U+202E: LRE/RLE/PDF/RLO/RLE (Embedding/Override controls)
- U+2066-U+2069: LRI/RLI/FSI/PDI (Isolate controls)
"""

from flywheel.formatter import _sanitize_text


class TestBidiControlSanitization:
    """Test that Unicode Bidi control characters are properly escaped."""

    def test_sanitize_text_escapes_lrm_rlm_u200e_u200f(self):
        """Test that LRM (U+200E) and RLM (U+200F) are escaped."""
        # LRM - Left-to-Right Mark
        assert _sanitize_text("\u200e") == r"\u200e"
        # RLM - Right-to-Left Mark
        assert _sanitize_text("\u200f") == r"\u200f"
        # In context
        assert _sanitize_text("hello\u200eworld") == r"hello\u200eworld"
        assert _sanitize_text("hello\u200fworld") == r"hello\u200fworld"

    def test_sanitize_text_escapes_embedding_overrides_u202a_u202e(self):
        """Test that LRE/RLE/PDF/RLO (U+202A-U+202E) are escaped."""
        # LRE - Left-to-Right Embedding (U+202A)
        assert _sanitize_text("\u202a") == r"\u202a"
        # RLE - Right-to-Left Embedding (U+202B)
        assert _sanitize_text("\u202b") == r"\u202b"
        # PDF - Pop Directional Format (U+202C)
        assert _sanitize_text("\u202c") == r"\u202c"
        # RLO - Right-to-Left Override (U+202D)
        assert _sanitize_text("\u202d") == r"\u202d"
        # LRO - Left-to-Right Override (U+202E)
        assert _sanitize_text("\u202e") == r"\u202e"
        # In context - RLO is commonly used in spoofing attacks
        assert _sanitize_text("evil\u202eexe.txt") == r"evil\u202eexe.txt"

    def test_sanitize_text_escapes_isolate_controls_u2066_u2069(self):
        """Test that LRI/RLI/FSI/PDI (U+2066-U+2069) are escaped."""
        # LRI - Left-to-Right Isolate (U+2066)
        assert _sanitize_text("\u2066") == r"\u2066"
        # RLI - Right-to-Left Isolate (U+2067)
        assert _sanitize_text("\u2067") == r"\u2067"
        # FSI - First Strong Isolate (U+2068)
        assert _sanitize_text("\u2068") == r"\u2068"
        # PDI - Pop Directional Isolate (U+2069)
        assert _sanitize_text("\u2069") == r"\u2069"
        # In context
        assert _sanitize_text("text\u2066inside\u2069end") == r"text\u2066inside\u2069end"

    def test_sanitize_text_bidi_with_other_controls(self):
        """Test that Bidi chars are escaped alongside other control characters."""
        # Mix of C0, C1, DEL, and Bidi controls
        assert _sanitize_text("a\u202e\x01b") == r"a\u202e\x01b"
        assert _sanitize_text("\u200e\x7f\u2069") == r"\u200e\x7f\u2069"

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes Bidi control characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        # RLO attack example - "exe.txt" would appear as "txt.exe"
        todo = Todo(id=1, text="evil\u202eexe.txt", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 evil\u202eexe.txt"

    def test_sanitize_text_escapes_all_bidi_ranges(self):
        """Test full Bidi ranges are escaped."""
        # Test all chars in U+200E-U+200F range
        for code in range(0x200E, 0x2010):
            char = chr(code)
            result = _sanitize_text(char)
            assert result == f"\\u{code:04x}", f"Expected \\u{code:04x}, got {result}"

        # Test all chars in U+202A-U+202E range
        for code in range(0x202A, 0x202F):
            char = chr(code)
            result = _sanitize_text(char)
            assert result == f"\\u{code:04x}", f"Expected \\u{code:04x}, got {result}"

        # Test all chars in U+2066-U+2069 range
        for code in range(0x2066, 0x206A):
            char = chr(code)
            result = _sanitize_text(char)
            assert result == f"\\u{code:04x}", f"Expected \\u{code:04x}, got {result}"
