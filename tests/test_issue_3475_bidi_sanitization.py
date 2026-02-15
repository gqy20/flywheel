"""Tests for BIDI control character sanitization (Issue #3475).

BIDI (bidirectional) control characters can be used for text direction
spoofing attacks where text is visually reordered to hide malicious content.
These characters should be sanitized to visible representations.

Character ranges:
- U+202A-U+202E: LRE, RLE, PDF, LRO, RLO (directional formatting)
- U+2066-U+2069: LRI, RLI, FSI, PDI (isolate formatting)
- U+200E-U+200F: LRM, RLM (directional marks)
"""

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBidiSanitization:
    """Test that BIDI control characters are properly escaped."""

    def test_sanitize_text_escapes_rlo_character(self):
        """Test that RLO (Right-to-Left Override, U+202E) is escaped."""
        # RLO can be used to reverse text visually: "Hello\u202eABCD" shows as "HelloDCBA"
        assert _sanitize_text("Hello\u202eABCD") == r"Hello\u202eABCD"

    def test_sanitize_text_escapes_lro_character(self):
        """Test that LRO (Left-to-Right Override, U+202D) is escaped."""
        assert _sanitize_text("Text\u202dMore") == r"Text\u202dMore"

    def test_sanitize_text_escapes_lre_character(self):
        """Test that LRE (Left-to-Right Embedding, U+202A) is escaped."""
        assert _sanitize_text("Start\u202aEnd") == r"Start\u202aEnd"

    def test_sanitize_text_escapes_rle_character(self):
        """Test that RLE (Right-to-Left Embedding, U+202B) is escaped."""
        assert _sanitize_text("Start\u202bEnd") == r"Start\u202bEnd"

    def test_sanitize_text_escapes_pdf_character(self):
        """Test that PDF (Pop Directional Format, U+202C) is escaped."""
        assert _sanitize_text("Start\u202cEnd") == r"Start\u202cEnd"

    def test_sanitize_text_escapes_lri_character(self):
        """Test that LRI (Left-to-Right Isolate, U+2066) is escaped."""
        assert _sanitize_text("Text\u2066Isolated") == r"Text\u2066Isolated"

    def test_sanitize_text_escapes_rli_character(self):
        """Test that RLI (Right-to-Left Isolate, U+2067) is escaped."""
        assert _sanitize_text("Text\u2067Isolated") == r"Text\u2067Isolated"

    def test_sanitize_text_escapes_fsi_character(self):
        """Test that FSI (First Strong Isolate, U+2068) is escaped."""
        assert _sanitize_text("Text\u2068Isolated") == r"Text\u2068Isolated"

    def test_sanitize_text_escapes_pdi_character(self):
        """Test that PDI (Pop Directional Isolate, U+2069) is escaped."""
        assert _sanitize_text("Text\u2069End") == r"Text\u2069End"

    def test_sanitize_text_escapes_lrm_character(self):
        """Test that LRM (Left-to-Right Mark, U+200E) is escaped."""
        assert _sanitize_text("Text\u200eMark") == r"Text\u200eMark"

    def test_sanitize_text_escapes_rlm_character(self):
        """Test that RLM (Right-to-Left Mark, U+200F) is escaped."""
        assert _sanitize_text("Text\u200fMark") == r"Text\u200fMark"

    def test_sanitize_text_bidi_spoofing_attack(self):
        """Test a realistic BIDI spoofing attack scenario.

        An attacker might use RLO to make "HelloABCD.exe" appear as "HelloDCBA.exe"
        to hide a malicious file extension.
        """
        malicious = "Hello\u202eABCD.exe"  # Visually shows as "HelloDCBA.exe"
        result = _sanitize_text(malicious)
        # After sanitization, the RLO character should be escaped
        assert "\u202e" not in result
        assert r"\u202e" in result
        # The text should be clearly distinguishable
        assert result == r"Hello\u202eABCD.exe"

    def test_sanitize_text_multiple_bidi_chars(self):
        """Test that multiple BIDI characters are all escaped."""
        text = "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\u200e\u200f"
        result = _sanitize_text(text)
        # All BIDI chars should be escaped
        assert "\u202a" not in result
        assert "\u202b" not in result
        assert "\u202c" not in result
        assert "\u202d" not in result
        assert "\u202e" not in result
        assert "\u2066" not in result
        assert "\u2067" not in result
        assert "\u2068" not in result
        assert "\u2069" not in result
        assert "\u200e" not in result
        assert "\u200f" not in result

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes BIDI control characters."""
        todo = Todo(id=1, text="Buy milk\u202e", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Buy milk\u202e"

    def test_bidi_with_other_control_chars(self):
        """Test that BIDI chars are escaped alongside other control characters."""
        # Mix of BIDI and C0 control characters
        result = _sanitize_text("a\u202e\nb\t\u2066")
        assert "\u202e" not in result
        assert "\u2066" not in result
        assert "\n" not in result
        assert "\t" not in result
        assert r"\u202e" in result
        assert r"\u2066" in result
        assert r"\n" in result
        assert r"\t" in result

    def test_valid_arabic_text_passes_through(self):
        """Test that valid Arabic (RTL) text is not affected."""
        # Regular Arabic text should pass through unchanged
        arabic = "مرحبا"  # "Hello" in Arabic
        assert _sanitize_text(arabic) == arabic

    def test_valid_hebrew_text_passes_through(self):
        """Test that valid Hebrew (RTL) text is not affected."""
        # Regular Hebrew text should pass through unchanged
        hebrew = "שלום"  # "Hello" in Hebrew
        assert _sanitize_text(hebrew) == hebrew

    def test_mixed_rtl_ltr_without_controls_passes(self):
        """Test that mixed RTL/LTR text without BIDI controls passes through."""
        # Mixed text without control characters should be unchanged
        text = "Hello مرحبا World"
        assert _sanitize_text(text) == text
