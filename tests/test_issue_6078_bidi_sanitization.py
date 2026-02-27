"""Tests for BIDI (Bi-Directional Text) control character sanitization (Issue #6078).

BIDI control characters enable text direction spoofing attacks where
malicious text can be rendered differently than expected, potentially
tricking users into executing dangerous actions.

Characters to sanitize:
- U+202A-U+202E: Embedding and override controls (LRE, RLE, PDF, LRO, RLO)
- U+2066-U+2069: Isolate controls (LRI, RLI, FSI, PDI)
- U+200E-U+200F: Mark controls (LRM, RLM)
"""

from flywheel.formatter import _sanitize_text


class TestBIDIControlSanitization:
    """Test that BIDI control characters are properly escaped."""

    def test_sanitize_text_escapes_rtl_override_u202e(self):
        """Test that RTL Override (U+202E) is escaped to prevent spoofing."""
        # U+202E is the Right-to-Left Override - can reverse text display
        assert _sanitize_text("\u202eABC") == r"\u202eABC"

    def test_sanitize_text_escapes_ltr_override_u202d(self):
        """Test that LTR Override (U+202D) is escaped."""
        assert _sanitize_text("\u202dXYZ") == r"\u202dXYZ"

    def test_sanitize_text_escapes_embedding_controls(self):
        """Test that LRE (U+202A) and RLE (U+202B) are escaped."""
        assert _sanitize_text("\u202atext") == r"\u202atext"
        assert _sanitize_text("\u202btext") == r"\u202btext"

    def test_sanitize_text_escapes_pop_directional_format_u202c(self):
        """Test that PDF (U+202C) is escaped."""
        assert _sanitize_text("text\u202c") == r"text\u202c"

    def test_sanitize_text_escapes_isolate_controls(self):
        """Test that isolate controls (U+2066-U+2069) are escaped."""
        # LRI (Left-to-Right Isolate)
        assert _sanitize_text("\u2066test") == r"\u2066test"
        # RLI (Right-to-Left Isolate)
        assert _sanitize_text("\u2067test") == r"\u2067test"
        # FSI (First Strong Isolate)
        assert _sanitize_text("\u2068test") == r"\u2068test"
        # PDI (Pop Directional Isolate)
        assert _sanitize_text("test\u2069") == r"test\u2069"

    def test_sanitize_text_escapes_mark_controls(self):
        """Test that LRM (U+200E) and RLM (U+200F) are escaped."""
        assert _sanitize_text("a\u200eb") == r"a\u200eb"
        assert _sanitize_text("a\u200fb") == r"a\u200fb"

    def test_sanitize_text_multiple_bidi_chars(self):
        """Test that multiple BIDI characters are all escaped."""
        # RTL override followed by isolate
        assert _sanitize_text("\u202e\u2066ABC") == r"\u202e\u2066ABC"

    def test_sanitize_text_bidi_with_normal_text(self):
        """Test BIDI chars are escaped in normal text context."""
        assert _sanitize_text("Hello\u202eWorld") == r"Hello\u202eWorld"

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes BIDI control characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        todo = Todo(id=1, text="Buy\u202emilk", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Buy\u202emilk"

    def test_bidi_spoofing_attack_prevented(self):
        """Test that a realistic BIDI spoofing attack is neutralized.

        Example: "execute.bat" with RTL override could appear as "tab.etucexe"
        """
        # The string "exe\u202ebat.pif" would render as "exe" + reversed "bat.pif"
        # After sanitization, the BIDI character should be escaped
        malicious = "script.\u202etxt"
        sanitized = _sanitize_text(malicious)
        assert sanitized == r"script.\u202etxt"
        # The escaped version will display the literal characters, not reversed
        assert "\u202e" not in sanitized
