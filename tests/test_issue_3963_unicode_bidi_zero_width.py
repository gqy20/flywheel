"""Tests for Unicode bidirectional and zero-width character sanitization (Issue #3963).

Unicode bidirectional override characters (U+202A-U+202E) and zero-width characters
(U+200B-U+200F) can be used for text spoofing attacks. They should be sanitized
to prevent potential security issues in terminal output.

Bidirectional override characters:
- U+202A: LEFT-TO-RIGHT EMBEDDING (LRE)
- U+202B: RIGHT-TO-LEFT EMBEDDING (RLE)
- U+202C: POP DIRECTIONAL FORMATTING (PDF)
- U+202D: LEFT-TO-RIGHT OVERRIDE (LRO)
- U+202E: RIGHT-TO-LEFT OVERRIDE (RLO)

Zero-width and directional formatting characters:
- U+200B: ZERO WIDTH SPACE
- U+200C: ZERO WIDTH NON-JOINER
- U+200D: ZERO WIDTH JOINER
- U+200E: LEFT-TO-RIGHT MARK
- U+200F: RIGHT-TO-LEFT MARK
"""

import pytest

from flywheel.formatter import _sanitize_text


class TestUnicodeBidiSanitization:
    """Test that Unicode bidirectional characters (U+202A-U+202E) are escaped."""

    def test_sanitize_text_escapes_right_to_left_override_u202e(self):
        """Test that RLO (U+202E) - used for text spoofing - is escaped."""
        # RLO is the most dangerous - can reverse text display
        assert _sanitize_text("eval\u202eLarry.exe") == r"eval\u202eLarry.exe"

    def test_sanitize_text_escapes_left_to_right_override_u202d(self):
        """Test that LRO (U+202D) is escaped."""
        assert _sanitize_text("text\u202dend") == r"text\u202dend"

    def test_sanitize_text_escapes_bidi_embeddings_u202a_u202b(self):
        """Test that LRE (U+202A) and RLE (U+202B) are escaped."""
        # LEFT-TO-RIGHT EMBEDDING
        assert _sanitize_text("start\u202aend") == r"start\u202aend"
        # RIGHT-TO-LEFT EMBEDDING
        assert _sanitize_text("start\u202bend") == r"start\u202bend"

    def test_sanitize_text_escapes_pop_directional_u202c(self):
        """Test that PDF (U+202C) is escaped."""
        assert _sanitize_text("text\u202cend") == r"text\u202cend"

    def test_sanitize_text_escapes_all_bidi_range_u202a_to_u202e(self):
        """Test that the full bidirectional range (U+202A-U+202E) is escaped."""
        for code in range(0x202A, 0x202F):
            char = chr(code)
            if code <= 0x202E:
                # These should be escaped
                assert _sanitize_text(f"a{char}b") == rf"a\u{code:04x}b"
            else:
                # U+202F and beyond should pass through
                assert _sanitize_text(f"a{char}b") == f"a{char}b"


class TestZeroWidthSanitization:
    """Test that zero-width characters (U+200B-U+200F) are escaped."""

    def test_sanitize_text_escapes_zero_width_space_u200b(self):
        """Test that zero-width space (U+200B) is escaped."""
        # Can be used to hide malicious content
        assert _sanitize_text("evil\u200bcode") == r"evil\u200bcode"

    def test_sanitize_text_escapes_zero_width_non_joiner_u200c(self):
        """Test that ZWNJ (U+200C) is escaped."""
        assert _sanitize_text("text\u200cend") == r"text\u200cend"

    def test_sanitize_text_escapes_zero_width_joiner_u200d(self):
        """Test that ZWJ (U+200D) is escaped."""
        assert _sanitize_text("text\u200dend") == r"text\u200dend"

    def test_sanitize_text_escapes_directional_marks_u200e_u200f(self):
        """Test that LRM (U+200E) and RLM (U+200F) are escaped."""
        # LEFT-TO-RIGHT MARK
        assert _sanitize_text("text\u200eend") == r"text\u200eend"
        # RIGHT-TO-LEFT MARK
        assert _sanitize_text("text\u200fend") == r"text\u200fend"

    def test_sanitize_text_escapes_all_zero_width_range_u200b_to_u200f(self):
        """Test that the full zero-width range (U+200B-U+200F) is escaped."""
        for code in range(0x200B, 0x2010):
            char = chr(code)
            assert _sanitize_text(f"a{char}b") == rf"a\u{code:04x}b"


class TestBidiAndZeroWidthInTodoFormatter:
    """Test that TodoFormatter properly escapes problematic Unicode characters."""

    def test_format_todo_escapes_bidi_rlo(self):
        """Test that RLO in todo text is escaped."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        # This would display as "eval.exeyrraL" without sanitization
        todo = Todo(id=1, text="eval\u202eLarry.exe", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 eval\u202eLarry.exe"

    def test_format_todo_escapes_zero_width_space(self):
        """Test that zero-width space in todo text is escaped."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        todo = Todo(id=1, text="test\u200bcase", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 test\u200bcase"

    def test_format_todo_with_mixed_controls(self):
        """Test that mixed control characters are all properly escaped."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        # Mix of C0, C1, bidi, and zero-width
        todo = Todo(id=1, text="a\x01b\u202ec\u200bd", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 a\x01b\u202ec\u200bd"


class TestNormalUnicodeUnaffected:
    """Test that normal Unicode text is not affected by the additional sanitization."""

    def test_normal_arabic_text_passes(self):
        """Test that normal Arabic text (which uses RTL) passes through."""
        # These are actual Arabic letters, not control characters
        assert _sanitize_text("مرحبا") == "مرحبا"

    def test_normal_hebrew_text_passes(self):
        """Test that normal Hebrew text passes through."""
        assert _sanitize_text("שלום") == "שלום"

    def test_normal_emoji_passes(self):
        """Test that emoji still passes through."""
        assert _sanitize_text("Hello 🎉 World") == "Hello 🎉 World"

    def test_nbsp_passes(self):
        """Test that non-breaking space (U+00A0) passes through."""
        # U+00A0 is a regular character, not a control character
        assert _sanitize_text("café\u00a0time") == "café\u00a0time"
