"""Regression tests for Issue #6199: BiDi override character sanitization.

BiDi (Bidirectional) override characters can be used to display text backwards
or change text direction, enabling visual spoofing attacks (e.g., 'exe.pac'
displayed as 'cap.exe'). These characters should be sanitized to prevent
such attacks.

BiDi characters that need sanitization:
- U+202A (LRE) - Left-to-Right Embedding
- U+202B (RLE) - Right-to-Left Embedding
- U+202C (PDF) - Pop Directional Formatting
- U+202D (LRO) - Left-to-Right Override
- U+202E (RLO) - Right-to-Left Override
- U+2066 (LRI) - Left-to-Right Isolate
- U+2067 (RLI) - Right-to-Left Isolate
- U+2068 (FSI) - First Strong Isolate
- U+2069 (PDI) - Pop Directional Isolate
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBiDiCharacterSanitization:
    """Test that BiDi override characters are properly escaped."""

    def test_sanitize_text_escapes_rlo_u202e(self):
        """Test that Right-to-Left Override (U+202E) is escaped."""
        # This is the most dangerous one - can reverse text display
        result = _sanitize_text("\u202eexe.pac")
        # Should contain escaped representation, not raw character
        assert "\\u202e" in result
        assert "\u202e" not in result

    def test_sanitize_text_escapes_lre_u202a(self):
        """Test that Left-to-Right Embedding (U+202A) is escaped."""
        result = _sanitize_text("normal\u202atext")
        assert "\\u202a" in result
        assert "\u202a" not in result

    def test_sanitize_text_escapes_rle_u202b(self):
        """Test that Right-to-Left Embedding (U+202B) is escaped."""
        result = _sanitize_text("normal\u202btext")
        assert "\\u202b" in result
        assert "\u202b" not in result

    def test_sanitize_text_escapes_pdf_u202c(self):
        """Test that Pop Directional Formatting (U+202C) is escaped."""
        result = _sanitize_text("normal\u202ctext")
        assert "\\u202c" in result
        assert "\u202c" not in result

    def test_sanitize_text_escapes_lro_u202d(self):
        """Test that Left-to-Right Override (U+202D) is escaped."""
        result = _sanitize_text("normal\u202dtext")
        assert "\\u202d" in result
        assert "\u202d" not in result

    def test_sanitize_text_escapes_lri_u2066(self):
        """Test that Left-to-Right Isolate (U+2066) is escaped."""
        result = _sanitize_text("normal\u2066text")
        assert "\\u2066" in result
        assert "\u2066" not in result

    def test_sanitize_text_escapes_rli_u2067(self):
        """Test that Right-to-Left Isolate (U+2067) is escaped."""
        result = _sanitize_text("normal\u2067text")
        assert "\\u2067" in result
        assert "\u2067" not in result

    def test_sanitize_text_escapes_fsi_u2068(self):
        """Test that First Strong Isolate (U+2068) is escaped."""
        result = _sanitize_text("normal\u2068text")
        assert "\\u2068" in result
        assert "\u2068" not in result

    def test_sanitize_text_escapes_pdi_u2069(self):
        """Test that Pop Directional Isolate (U+2069) is escaped."""
        result = _sanitize_text("normal\u2069text")
        assert "\\u2069" in result
        assert "\u2069" not in result

    def test_sanitize_text_all_bidi_chars_together(self):
        """Test that all BiDi characters in a string are escaped."""
        bidi_string = "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
        result = _sanitize_text(bidi_string)
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
        # None of the raw characters should be present
        for char in bidi_string:
            assert char not in result

    def test_format_todo_with_bidi_spoofing_attack(self):
        """Test that format_todo sanitizes BiDi spoofing attack."""
        # Simulate an attack: 'exe.pac' displayed backwards as 'cap.exe'
        todo = Todo(id=1, text="\u202eexe.pac", done=False)
        result = TodoFormatter.format_todo(todo)
        # Should contain escaped representation
        assert "\\u202e" in result
        assert "\u202e" not in result
        # Should show the escaped version, not the raw character
        assert result == r"[ ]   1 \u202eexe.pac"

    def test_literal_backslash_u_distinct_from_actual_bidi(self):
        """Test that literal backslash + 'u202e' is distinguishable from actual U+202E."""
        # Literal backslash followed by 'u202e' text
        literal_result = _sanitize_text("\\u202e")
        # Actual U+202E character
        bidi_result = _sanitize_text("\u202e")

        # They should produce different outputs
        # The literal backslash gets escaped to \\
        assert literal_result == "\\\\u202e"
        # The actual BiDi char gets escaped to \u202e
        assert bidi_result == "\\u202e"
        # They should NOT be the same
        assert literal_result != bidi_result

    def test_bidi_with_other_control_chars(self):
        """Test that BiDi chars are escaped alongside other control characters."""
        # Mix of BiDi, C0 controls, and normal text
        result = _sanitize_text("a\u202e\x01b\x7fc")
        assert "\\u202e" in result
        assert "\\x01" in result
        assert "\\x7f" in result
        assert "\u202e" not in result
        assert "\x01" not in result
        assert "\x7f" not in result

    def test_normal_unicode_not_affected(self):
        """Test that normal Unicode characters pass through unchanged."""
        # Various Unicode characters that should NOT be escaped
        assert _sanitize_text("café") == "café"
        assert _sanitize_text("日本語") == "日本語"
        assert _sanitize_text("🎉") == "🎉"
        assert _sanitize_text("€→✓") == "€→✓"
