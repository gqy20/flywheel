"""Tests for BIDI control character sanitization (Issue #6078).

BIDI (Bi-Directional Text) control characters can be used to manipulate
text direction display, enabling text direction spoofing attacks.
These characters should be escaped to prevent such attacks.

BIDI control characters include:
- U+200E: LEFT-TO-RIGHT MARK (LRM)
- U+200F: RIGHT-TO-LEFT MARK (RLM)
- U+202A: LEFT-TO-RIGHT EMBEDDING (LRE)
- U+202B: RIGHT-TO-LEFT EMBEDDING (RLE)
- U+202C: POP DIRECTIONAL FORMATTING (PDF)
- U+202D: LEFT-TO-RIGHT OVERRIDE (LRO)
- U+202E: RIGHT-TO-LEFT OVERRIDE (RLO)
- U+2066: LEFT-TO-RIGHT ISOLATE (LRI)
- U+2067: RIGHT-TO-LEFT ISOLATE (RLI)
- U+2068: FIRST STRONG ISOLATE (FSI)
- U+2069: POP DIRECTIONAL ISOLATE (PDI)
"""

from flywheel.formatter import _sanitize_text


class TestBidiControlSanitization:
    """Test that BIDI control characters are properly escaped."""

    def test_sanitize_text_escapes_rtl_override_u202e(self):
        """Test that RLO (U+202E) - a common spoofing attack vector - is escaped."""
        # U+202E is the Right-to-Left Override character
        # Attack: "CBA" displayed as "ABC" using RLO
        assert _sanitize_text("\u202eABC") == r"\u202eABC"

    def test_sanitize_text_escapes_ltr_override_u202d(self):
        """Test that LRO (U+202D) is escaped."""
        assert _sanitize_text("\u202dXYZ") == r"\u202dXYZ"

    def test_sanitize_text_escapes_bidi_embedding_chars(self):
        """Test LRE (U+202A), RLE (U+202B), and PDF (U+202C) are escaped."""
        assert _sanitize_text("\u202atext") == r"\u202atext"
        assert _sanitize_text("\u202btext") == r"\u202btext"
        assert _sanitize_text("\u202ctext") == r"\u202ctext"

    def test_sanitize_text_escapes_bidi_isolate_chars(self):
        """Test LRI, RLI, FSI, and PDI (U+2066-U+2069) are escaped."""
        assert _sanitize_text("\u2066test") == r"\u2066test"
        assert _sanitize_text("\u2067test") == r"\u2067test"
        assert _sanitize_text("\u2068test") == r"\u2068test"
        assert _sanitize_text("test\u2069") == r"test\u2069"

    def test_sanitize_text_escapes_bidi_marks(self):
        """Test LRM (U+200E) and RLM (U+200F) are escaped."""
        assert _sanitize_text("\u200etest") == r"\u200etest"
        assert _sanitize_text("\u200ftest") == r"\u200ftest"

    def test_sanitize_text_escapes_all_bidi_chars_in_string(self):
        """Test multiple BIDI chars in a single string are all escaped."""
        # Mix of various BIDI chars
        input_text = "a\u202eb\u2066c\u200ed"
        expected = r"a\u202eb\u2066c\u200ed"
        assert _sanitize_text(input_text) == expected

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes BIDI control characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        # RLO attack vector - "ABC" displayed backwards as "CBA"
        todo = Todo(id=1, text="Pay \u202eABC", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Pay \u202eABC"

    def test_bidi_attack_vector_spoofing_prevented(self):
        """Test that BIDI-based text direction spoofing attacks are prevented.

        A common attack: displaying "exe.txt" as "txt.exe" using RLO
        """
        # Without sanitization: "txt\u202eexe." would display as "txt.exe"
        # With sanitization: it should show escaped form
        malicious = "txt\u202eexe."
        sanitized = _sanitize_text(malicious)
        assert sanitized == r"txt\u202eexe."
        # Verify the RLO character is not present in output
        assert "\u202e" not in sanitized
