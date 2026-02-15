"""Tests for BIDI control character sanitization (Issue #3475).

BIDI control characters can be used for text direction spoofing attacks
(Trojan Source, CVE-2021-42573). They should be sanitized to prevent
visual text manipulation.

Unicode BIDI control characters:
- U+200E-U+200F: LRM (Left-to-Right Mark), RLM (Right-to-Left Mark)
- U+202A-U+202E: LRE, RLE, PDF, LRO, RLO (bidirectional formatting)
- U+2066-U+2069: LRI, RLI, FSI, PDI (isolated bidirectional formatting)
"""

from flywheel.formatter import _sanitize_text


class TestBIDIControlSanitization:
    """Test that BIDI control characters are properly escaped."""

    def test_sanitize_text_escapes_rlo_u202e(self):
        """Test RLO (Right-to-Left Override) is escaped.

        This is a critical security test - RLO can reverse text display.
        Example: 'Hello\u202eABCD.exe' displays as 'Helloexe.DCBA'
        """
        assert _sanitize_text("Hello\u202eABCD.exe") == r"Hello\u202eABCD.exe"

    def test_sanitize_text_escapes_lro_u202d(self):
        """Test LRO (Left-to-Right Override) is escaped."""
        assert _sanitize_text("text\u202dmore") == r"text\u202dmore"

    def test_sanitize_text_escapes_lre_u202a(self):
        """Test LRE (Left-to-Right Embedding) is escaped."""
        assert _sanitize_text("start\u202aend") == r"start\u202aend"

    def test_sanitize_text_escapes_rle_u202b(self):
        """Test RLE (Right-to-Left Embedding) is escaped."""
        assert _sanitize_text("start\u202bend") == r"start\u202bend"

    def test_sanitize_text_escapes_pdf_u202c(self):
        """Test PDF (Pop Directional Format) is escaped."""
        assert _sanitize_text("start\u202cend") == r"start\u202cend"

    def test_sanitize_text_escapes_lrm_u200e(self):
        """Test LRM (Left-to-Right Mark) is escaped."""
        assert _sanitize_text("text\u200emore") == r"text\u200emore"

    def test_sanitize_text_escapes_rlm_u200f(self):
        """Test RLM (Right-to-Left Mark) is escaped."""
        assert _sanitize_text("text\u200fmore") == r"text\u200fmore"

    def test_sanitize_text_escapes_lri_u2066(self):
        """Test LRI (Left-to-Right Isolate) is escaped."""
        assert _sanitize_text("start\u2066end") == r"start\u2066end"

    def test_sanitize_text_escapes_rli_u2067(self):
        """Test RLI (Right-to-Left Isolate) is escaped."""
        assert _sanitize_text("start\u2067end") == r"start\u2067end"

    def test_sanitize_text_escapes_fsi_u2068(self):
        """Test FSI (First Strong Isolate) is escaped."""
        assert _sanitize_text("start\u2068end") == r"start\u2068end"

    def test_sanitize_text_escapes_pdi_u2069(self):
        """Test PDI (Pop Directional Isolate) is escaped."""
        assert _sanitize_text("start\u2069end") == r"start\u2069end"

    def test_sanitize_text_escapes_full_bidi_range(self):
        """Test all BIDI ranges are covered: U+200E-200F, U+202A-202E, U+2066-2069."""
        # Combined test for full coverage
        text = "\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
        result = _sanitize_text(text)
        # All should be escaped
        assert result == (
            r"\u200e\u200f\u202a\u202b\u202c\u202d\u202e"
            r"\u2066\u2067\u2068\u2069"
        )

    def test_sanitize_text_bidi_spoofing_attack(self):
        """Test a realistic BIDI spoofing attack scenario.

        Attack: 'important\u202edoc.exe' would display as 'importantexe.cod'
        which could trick users into running an executable.
        """
        malicious = "important\u202edoc.exe"
        result = _sanitize_text(malicious)
        # The RLO character must be escaped to prevent visual spoofing
        assert "\u202e" not in result
        assert r"\u202e" in result

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes BIDI control characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        todo = Todo(id=1, text="Safe\u202eMalicious", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Safe\u202eMalicious"

    def test_bidi_with_other_control_chars(self):
        """Test BIDI chars are escaped alongside other control characters."""
        # Mix of BIDI (U+202E), C0 (0x1b), and normal text
        assert _sanitize_text("a\u202eb\x1bc") == r"a\u202eb\x1bc"
