"""Tests for BiDi character sanitization (Issue #6199).

BiDi (Bidirectional) override characters can be used for visual spoofing attacks
by making text display backwards or change direction. For example, 'exe.pac'
displayed as 'cap.exe'. These characters should be sanitized to prevent such attacks.

BiDi characters to sanitize:
- U+202A (LRE - Left-to-Right Embedding)
- U+202B (RLE - Right-to-Left Embedding)
- U+202C (PDF - Pop Directional Formatting)
- U+202D (LRO - Left-to-Right Override)
- U+202E (RLO - Right-to-Left Override)
- U+2066 (LRI - Left-to-Right Isolate)
- U+2067 (RLI - Right-to-Left Isolate)
- U+2068 (FSI - First Strong Isolate)
- U+2069 (PDI - Pop Directional Isolate)
"""

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBiDiSanitization:
    """Test that BiDi override characters are properly escaped."""

    def test_sanitize_text_escapes_rlo_u202e(self):
        """Test that U+202E (RLO - Right-to-Left Override) is escaped."""
        # RLO can make 'exe.pac' display as 'cap.exe' - dangerous for spoofing
        result = _sanitize_text("\u202eexe.pac")
        assert "\\u202e" in result
        assert "\u202e" not in result

    def test_sanitize_text_escapes_lro_u202d(self):
        """Test that U+202D (LRO - Left-to-Right Override) is escaped."""
        result = _sanitize_text("\u202dtext")
        assert "\\u202d" in result
        assert "\u202d" not in result

    def test_sanitize_text_escapes_lre_u202a(self):
        """Test that U+202A (LRE - Left-to-Right Embedding) is escaped."""
        result = _sanitize_text("\u202atext")
        assert "\\u202a" in result
        assert "\u202a" not in result

    def test_sanitize_text_escapes_rle_u202b(self):
        """Test that U+202B (RLE - Right-to-Left Embedding) is escaped."""
        result = _sanitize_text("\u202btext")
        assert "\\u202b" in result
        assert "\u202b" not in result

    def test_sanitize_text_escapes_pdf_u202c(self):
        """Test that U+202C (PDF - Pop Directional Formatting) is escaped."""
        result = _sanitize_text("\u202ctext")
        assert "\\u202c" in result
        assert "\u202c" not in result

    def test_sanitize_text_escapes_lri_u2066(self):
        """Test that U+2066 (LRI - Left-to-Right Isolate) is escaped."""
        result = _sanitize_text("\u2066text")
        assert "\\u2066" in result
        assert "\u2066" not in result

    def test_sanitize_text_escapes_rli_u2067(self):
        """Test that U+2067 (RLI - Right-to-Left Isolate) is escaped."""
        result = _sanitize_text("\u2067text")
        assert "\\u2067" in result
        assert "\u2067" not in result

    def test_sanitize_text_escapes_fsi_u2068(self):
        """Test that U+2068 (FSI - First Strong Isolate) is escaped."""
        result = _sanitize_text("\u2068text")
        assert "\\u2068" in result
        assert "\u2068" not in result

    def test_sanitize_text_escapes_pdi_u2069(self):
        """Test that U+2069 (PDI - Pop Directional Isolate) is escaped."""
        result = _sanitize_text("\u2069text")
        assert "\\u2069" in result
        assert "\u2069" not in result

    def test_sanitize_text_escapes_all_bidi_chars(self):
        """Test that all BiDi override characters are escaped together."""
        bidi_text = "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
        result = _sanitize_text(bidi_text)
        # All should be escaped
        assert "\\u202a" in result
        assert "\\u202b" in result
        assert "\\u202c" in result
        assert "\\u202d" in result
        assert "\\u202e" in result
        assert "\\u2066" in result
        assert "\\u2067" in result
        assert "\\u2068" in result
        assert "\\u2069" in result
        # No raw BiDi characters should remain
        for char in bidi_text:
            assert char not in result

    def test_sanitize_text_bidi_with_normal_text(self):
        """Test that BiDi chars in normal text are escaped but text remains."""
        result = _sanitize_text("Hello\u202eWorld")
        assert "\\u202e" in result
        assert "Hello" in result
        assert "World" in result
        assert "\u202e" not in result

    def test_format_todo_with_bidi_chars(self):
        """Test that format_todo properly escapes BiDi characters."""
        # Simulated attack: filename that displays backwards
        todo = Todo(id=1, text="Download \u202eexe.pac", done=False)
        result = TodoFormatter.format_todo(todo)
        assert "\\u202e" in result
        assert "\u202e" not in result
        assert "Download" in result
        assert "exe.pac" in result

    def test_literal_backslash_u_different_from_actual_unicode(self):
        """Test that literal backslash-u text is distinguishable from actual BiDi chars.

        This ensures that '\\u202e' (literal text) produces different output
        than actual U+202E character.
        """
        # Actual Unicode character
        actual_unicode = _sanitize_text("\u202e")
        # Literal backslash-u text (user typed this)
        literal_text = _sanitize_text("\\u202e")
        # These should produce different outputs
        # Actual unicode should be escaped to \\u202e representation
        # Literal text should have backslash doubled
        assert actual_unicode == r"\u202e"
        assert literal_text == r"\\u202e"
        assert actual_unicode != literal_text

    def test_bidi_spoofing_attack_example(self):
        """Test a realistic BiDi spoofing attack scenario.

        An attacker might use RLO to make a malicious filename appear legitimate.
        E.g., 'photo\u202egpj.exe' would display as 'photoexe.jpg'
        """
        malicious_filename = "photo\u202egpj.exe"
        result = _sanitize_text(malicious_filename)
        # The RLO character should be escaped
        assert "\\u202e" in result
        assert "\u202e" not in result
        # The actual text content should remain visible
        assert "photo" in result
        assert "gpj.exe" in result
