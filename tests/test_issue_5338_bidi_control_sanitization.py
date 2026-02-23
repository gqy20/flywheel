"""Tests for Bidi Unicode control character sanitization (Issue #5338).

Bidi (bidirectional) Unicode control characters can be exploited for
text direction spoofing attacks. These characters should be sanitized
to prevent malicious text from appearing different than it renders.

Character ranges to sanitize:
- U+200E-U+200F: LRM (Left-to-Right Mark), RLM (Right-to-Left Mark)
- U+202A-U+202E: LRE, RLE, PDF, LRO, RLO (bidi embedding/override controls)
- U+2066-U+2069: LRI, RLI, FSI, PDI (bidi isolate controls)
"""

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBidiControlSanitization:
    """Test that Bidi Unicode control characters are properly escaped."""

    # U+200E-U+200F: LRM, RLM
    def test_sanitize_text_escapes_lrm_u200e(self):
        """Test that Left-to-Right Mark (U+200E) is escaped."""
        assert _sanitize_text("hello\u200eworld") == r"hello\u200eworld"

    def test_sanitize_text_escapes_rlm_u200f(self):
        """Test that Right-to-Left Mark (U+200F) is escaped."""
        assert _sanitize_text("hello\u200fworld") == r"hello\u200fworld"

    # U+202A-U+202E: LRE, RLE, PDF, LRO, RLO
    def test_sanitize_text_escapes_lre_u202a(self):
        """Test that Left-to-Right Embedding (U+202A) is escaped."""
        assert _sanitize_text("text\u202aafter") == r"text\u202aafter"

    def test_sanitize_text_escapes_rle_u202b(self):
        """Test that Right-to-Left Embedding (U+202B) is escaped."""
        assert _sanitize_text("text\u202bafter") == r"text\u202bafter"

    def test_sanitize_text_escapes_pdf_u202c(self):
        """Test that Pop Directional Formatting (U+202C) is escaped."""
        assert _sanitize_text("text\u202cafter") == r"text\u202cafter"

    def test_sanitize_text_escapes_lro_u202d(self):
        """Test that Left-to-Right Override (U+202D) is escaped."""
        assert _sanitize_text("text\u202dafter") == r"text\u202dafter"

    def test_sanitize_text_escapes_rlo_u202e(self):
        """Test that Right-to-Left Override (U+202E) - the most dangerous one - is escaped."""
        # RLO is commonly used for spoofing attacks
        assert _sanitize_text("hello\u202eworld") == r"hello\u202eworld"

    # U+2066-U+2069: LRI, RLI, FSI, PDI
    def test_sanitize_text_escapes_lri_u2066(self):
        """Test that Left-to-Right Isolate (U+2066) is escaped."""
        assert _sanitize_text("text\u2066after") == r"text\u2066after"

    def test_sanitize_text_escapes_rli_u2067(self):
        """Test that Right-to-Left Isolate (U+2067) is escaped."""
        assert _sanitize_text("text\u2067after") == r"text\u2067after"

    def test_sanitize_text_escapes_fsi_u2068(self):
        """Test that First Strong Isolate (U+2068) is escaped."""
        assert _sanitize_text("text\u2068after") == r"text\u2068after"

    def test_sanitize_text_escapes_pdi_u2069(self):
        """Test that Pop Directional Isolate (U+2069) is escaped."""
        assert _sanitize_text("text\u2069after") == r"text\u2069after"

    def test_sanitize_text_bidi_full_range(self):
        """Test that the full range of bidi characters is escaped."""
        # Test boundary cases
        # U+200D is NOT a bidi control (it's ZWJ - Zero Width Joiner)
        assert _sanitize_text("text\u200dafter") == "text\u200dafter"
        # U+200E is a bidi control
        assert _sanitize_text("text\u200eafter") == r"text\u200eafter"
        # U+2065 is undefined, should pass through
        assert _sanitize_text("text\u2065after") == "text\u2065after"
        # U+206A is NOT a bidi control
        assert _sanitize_text("text\u206aafter") == "text\u206aafter"

    def test_sanitize_text_multiple_bidi_chars(self):
        """Test that multiple bidi characters are all escaped."""
        result = _sanitize_text("\u202e\u2067\u200e")
        assert result == r"\u202e\u2067\u200e"

    def test_sanitize_text_bidi_with_other_controls(self):
        """Test that bidi chars are escaped alongside other control characters."""
        # Mix of C0, C1, DEL, and bidi controls
        result = _sanitize_text("a\x01b\x80c\u202ed")
        assert result == r"a\x01b\x80c\u202ed"

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes bidi control characters."""
        todo = Todo(id=1, text="Buy milk\u202e", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Buy milk\u202e"

    def test_rtl_spoofing_attack_neutralized(self):
        """Test a realistic RTL spoofing attack is neutralized.

        Without sanitization, this string could display as " trustworthy.com "
        when rendered from right-to-left, potentially misleading users.
        """
        # Simulate an attack string with RLO
        attack_string = "moc.yltneuqerpmi\u202eexe"
        result = _sanitize_text(attack_string)
        # The RLO should be escaped, not rendered
        assert "\u202e" not in result
        assert r"\u202e" in result

    def test_valid_unicode_still_passes(self):
        """Test that valid Unicode text (non-control) still passes through."""
        # Ensure we didn't break normal Unicode handling
        assert _sanitize_text("こんにちは") == "こんにちは"
        assert _sanitize_text("café") == "café"
        assert _sanitize_text("🎉") == "🎉"
        # Arabic text (which is naturally RTL) should pass through
        assert _sanitize_text("مرحبا") == "مرحبا"
        # Hebrew text (which is naturally RTL) should pass through
        assert _sanitize_text("שלום") == "שלום"
