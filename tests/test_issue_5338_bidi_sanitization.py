"""Tests for Bidi Unicode control character sanitization (Issue #5338).

Bidirectional (Bidi) Unicode control characters can be used to spoof
text direction and hide malicious content. These characters should be
sanitized to prevent text direction spoofing attacks.

Bidi control characters:
- U+202A-U+202E: Bidirectional formatting controls (LRE, RLE, PDF, LRO, RLO)
- U+2066-U+2069: Isolate controls (LRI, RLI, FSI, PDI)
- U+200E-U+200F: Directional marks (LRM, RLM)
"""

from flywheel.formatter import _sanitize_text


class TestBidiControlSanitization:
    """Test that Bidi Unicode control characters are properly escaped."""

    def test_sanitize_text_escapes_rlo_u202e(self):
        """Test that Right-to-Left Override (U+202E) is escaped.

        RLO is the most dangerous bidi character as it can reverse text
        direction to hide malicious content.
        """
        # RLO (U+202E) - Right-to-Left Override
        result = _sanitize_text("hello\u202eworld")
        assert "\\u202e" in result
        assert "\u202e" not in result

    def test_sanitize_text_escapes_lro_u202d(self):
        """Test that Left-to-Right Override (U+202D) is escaped."""
        # LRO (U+202D) - Left-to-Right Override
        result = _sanitize_text("text\u202dmore")
        assert "\\u202d" in result
        assert "\u202d" not in result

    def test_sanitize_text_escapes_lre_u202a(self):
        """Test that Left-to-Right Embedding (U+202A) is escaped."""
        # LRE (U+202A) - Left-to-Right Embedding
        result = _sanitize_text("start\u202aend")
        assert "\\u202a" in result
        assert "\u202a" not in result

    def test_sanitize_text_escapes_rle_u202b(self):
        """Test that Right-to-Left Embedding (U+202B) is escaped."""
        # RLE (U+202B) - Right-to-Left Embedding
        result = _sanitize_text("start\u202bend")
        assert "\\u202b" in result
        assert "\u202b" not in result

    def test_sanitize_text_escapes_pdf_u202c(self):
        """Test that Pop Directional Formatting (U+202C) is escaped."""
        # PDF (U+202C) - Pop Directional Formatting
        result = _sanitize_text("start\u202cend")
        assert "\\u202c" in result
        assert "\u202c" not in result

    def test_sanitize_text_escapes_isolate_controls_u2066_u2069(self):
        """Test that isolate controls (U+2066-U+2069) are escaped."""
        # LRI (U+2066) - Left-to-Right Isolate
        result = _sanitize_text("text\u2066more")
        assert "\\u2066" in result
        assert "\u2066" not in result

        # RLI (U+2067) - Right-to-Left Isolate
        result = _sanitize_text("text\u2067more")
        assert "\\u2067" in result
        assert "\u2067" not in result

        # FSI (U+2068) - First Strong Isolate
        result = _sanitize_text("text\u2068more")
        assert "\\u2068" in result
        assert "\u2068" not in result

        # PDI (U+2069) - Pop Directional Isolate
        result = _sanitize_text("text\u2069more")
        assert "\\u2069" in result
        assert "\u2069" not in result

    def test_sanitize_text_escapes_directional_marks_u200e_u200f(self):
        """Test that directional marks (U+200E-U+200F) are escaped."""
        # LRM (U+200E) - Left-to-Right Mark
        result = _sanitize_text("text\u200emore")
        assert "\\u200e" in result
        assert "\u200e" not in result

        # RLM (U+200F) - Right-to-Left Mark
        result = _sanitize_text("text\u200fmore")
        assert "\\u200f" in result
        assert "\u200f" not in result

    def test_sanitize_text_bidi_with_other_controls(self):
        """Test that bidi chars are escaped alongside other control characters."""
        # Mix of C0 (0x01), bidi (U+202E), and C1 (0x80)
        result = _sanitize_text("a\x01b\u202ec\x80d")
        assert "\\x01" in result
        assert "\\u202e" in result
        assert "\\x80" in result

    def test_sanitize_text_rtl_spoofing_attack_vector(self):
        """Test that RTL override attack vectors are neutralized.

        Example: "Buy milk" followed by RLO could display as "klim yuB"
        potentially hiding malicious intent.
        """
        # Simulate an attack using RLO to reverse text
        malicious = "Buy milk\u202eEXE.exe"
        result = _sanitize_text(malicious)
        # The RLO character should be escaped, not passed through
        assert "\\u202e" in result
        assert "\u202e" not in result
        # The text should be visible as-is, not reversed
        assert "Buy milk" in result

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes bidi control characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        todo = Todo(id=1, text="Buy milk\u202eEXE.exe", done=False)
        result = TodoFormatter.format_todo(todo)
        assert "\\u202e" in result
        assert "\u202e" not in result

    def test_all_bidi_range_202a_to_202e(self):
        """Test the entire U+202A-U+202E range."""
        for code in range(0x202A, 0x202F):
            char = chr(code)
            result = _sanitize_text(f"text{char}end")
            assert f"\\u{code:04x}" in result, f"U+{code:04X} was not escaped"
            assert char not in result, f"U+{code:04X} passed through unescaped"

    def test_all_bidi_range_2066_to_2069(self):
        """Test the entire U+2066-U+2069 range."""
        for code in range(0x2066, 0x206A):
            char = chr(code)
            result = _sanitize_text(f"text{char}end")
            assert f"\\u{code:04x}" in result, f"U+{code:04X} was not escaped"
            assert char not in result, f"U+{code:04X} passed through unescaped"

    def test_all_bidi_range_200e_to_200f(self):
        """Test the U+200E-U+200F range."""
        for code in range(0x200E, 0x2010):
            char = chr(code)
            result = _sanitize_text(f"text{char}end")
            assert f"\\u{code:04x}" in result, f"U+{code:04X} was not escaped"
            assert char not in result, f"U+{code:04X} passed through unescaped"


class TestBidiSanitizationNoRegression:
    """Ensure existing functionality still works after bidi sanitization."""

    def test_valid_unicode_still_passes(self):
        """Test that valid Unicode still passes through unchanged."""
        # These should NOT be escaped
        assert _sanitize_text("こんにちは") == "こんにちは"
        assert _sanitize_text("café") == "café"
        assert _sanitize_text("🎉") == "🎉"
        assert _sanitize_text("你好") == "你好"

    def test_c0_c1_controls_still_escaped(self):
        """Test that C0 and C1 controls are still escaped."""
        # C0 (0x01)
        assert _sanitize_text("\x01") == r"\x01"
        # DEL (0x7f)
        assert _sanitize_text("\x7f") == r"\x7f"
        # C1 (0x80)
        assert _sanitize_text("\x80") == r"\x80"

    def test_newlines_tabs_still_work(self):
        """Test that newlines and tabs are still escaped properly."""
        assert _sanitize_text("line1\nline2") == r"line1\nline2"
        assert _sanitize_text("col1\tcol2") == r"col1\tcol2"
