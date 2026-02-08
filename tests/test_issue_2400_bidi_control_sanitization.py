"""Regression tests for Issue #2400: Unicode bidirectional control character sanitization.

This test file ensures that Unicode bidirectional control characters
(U+202A-U+202E, U+2066-U+2069) are properly escaped to prevent trojan source
spoofing attacks.

Trojan source attacks use bidi control characters to hide malicious code
by making it appear as benign code in editors. These characters can:
1. Reverse the display order of text (RLO, LRO)
2. Embed text with different directionality (RLE, LRE)
3. Create isolated directional text runs (RLI, LRI, FSI)
4. Override formatting in ways that mislead reviewers (PDI, PDF)

Reference: https://trojansource.codes/
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBidiControlSanitization:
    """Test that Unicode bidirectional control characters are properly escaped."""

    def test_sanitize_text_escapes_u202a_lre(self):
        """LEFT-TO-RIGHT EMBEDDING (U+202A) must be escaped."""
        result = _sanitize_text("before\u202aafter")
        assert "\u202a" not in result, "U+202A (LRE) must be escaped"
        assert "\\u202a" in result, "U+202A should be escaped to \\u202a"

    def test_sanitize_text_escapes_u202b_rle(self):
        """RIGHT-TO-LEFT EMBEDDING (U+202B) must be escaped."""
        result = _sanitize_text("before\u202bafter")
        assert "\u202b" not in result, "U+202B (RLE) must be escaped"
        assert "\\u202b" in result, "U+202B should be escaped to \\u202b"

    def test_sanitize_text_escapes_u202c_pdf(self):
        """POP DIRECTIONAL FORMAT (U+202C) must be escaped."""
        result = _sanitize_text("before\u202cafter")
        assert "\u202c" not in result, "U+202C (PDF) must be escaped"
        assert "\\u202c" in result, "U+202C should be escaped to \\u202c"

    def test_sanitize_text_escapes_u202d_lro(self):
        """LEFT-TO-RIGHT OVERRIDE (U+202D) must be escaped."""
        result = _sanitize_text("before\u202dafter")
        assert "\u202d" not in result, "U+202D (LRO) must be escaped"
        assert "\\u202d" in result, "U+202D should be escaped to \\u202d"

    def test_sanitize_text_escapes_u202e_rlo(self):
        """RIGHT-TO-LEFT OVERRIDE (U+202E) must be escaped."""
        result = _sanitize_text("before\u202eafter")
        assert "\u202e" not in result, "U+202E (RLO) must be escaped"
        assert "\\u202e" in result, "U+202E should be escaped to \\u202e"

    def test_sanitize_text_escapes_u2066_lri(self):
        """LEFT-TO-RIGHT ISOLATE (U+2066) must be escaped."""
        result = _sanitize_text("before\u2066after")
        assert "\u2066" not in result, "U+2066 (LRI) must be escaped"
        assert "\\u2066" in result, "U+2066 should be escaped to \\u2066"

    def test_sanitize_text_escapes_u2067_rli(self):
        """RIGHT-TO-LEFT ISOLATE (U+2067) must be escaped."""
        result = _sanitize_text("before\u2067after")
        assert "\u2067" not in result, "U+2067 (RLI) must be escaped"
        assert "\\u2067" in result, "U+2067 should be escaped to \\u2067"

    def test_sanitize_text_escapes_u2068_fsi(self):
        """FIRST STRONG ISOLATE (U+2068) must be escaped."""
        result = _sanitize_text("before\u2068after")
        assert "\u2068" not in result, "U+2068 (FSI) must be escaped"
        assert "\\u2068" in result, "U+2068 should be escaped to \\u2068"

    def test_sanitize_text_escapes_u2069_pdi(self):
        """POP DIRECTIONAL ISOLATE (U+2069) must be escaped."""
        result = _sanitize_text("before\u2069after")
        assert "\u2069" not in result, "U+2069 (PDI) must be escaped"
        assert "\\u2069" in result, "U+2069 should be escaped to \\u2069"

    def test_sanitize_text_mixed_bidi_controls(self):
        """Multiple bidi control characters should all be escaped."""
        result = _sanitize_text("normal\u202a\u202e\u2066text")
        assert "\u202a" not in result
        assert "\u202e" not in result
        assert "\u2066" not in result
        assert "\\u202a" in result
        assert "\\u202e" in result
        assert "\\u2066" in result

    def test_sanitize_text_bidi_with_ascii_controls(self):
        """Bidi controls should be escaped alongside ASCII control characters."""
        result = _sanitize_text("\x01\u202a\n\u202e")
        # All control characters should be escaped
        assert "\x01" not in result
        assert "\u202a" not in result
        assert "\n" not in result
        assert "\u202e" not in result
        assert "\\x01" in result
        assert "\\u202a" in result
        assert "\\n" in result
        assert "\\u202e" in result

    def test_normal_unicode_passes_through_unchanged(self):
        """Valid Unicode text must NOT be affected by sanitization."""
        # Chinese characters
        assert _sanitize_text("你好世界") == "你好世界"
        # Japanese characters
        assert _sanitize_text("こんにちは") == "こんにちは"
        # Korean characters
        assert _sanitize_text("안녕하세요") == "안녕하세요"
        # Arabic (RTL language text - not control chars)
        assert _sanitize_text("مرحبا") == "مرحبا"
        # Hebrew (RTL language text - not control chars)
        assert _sanitize_text("שלום") == "שלום"
        # Emojis
        assert _sanitize_text("Hello 🎉 world 🌍") == "Hello 🎉 world 🌍"
        # Mixed scripts
        assert _sanitize_text("Buy café and 日本語") == "Buy café and 日本語"

    def test_format_todo_escapes_bidi_controls(self):
        """TodoFormatter should properly escape bidi control characters."""
        todo = Todo(id=1, text="Buy milk\u202eFAKE", done=False)
        result = TodoFormatter.format_todo(todo)
        # Should NOT contain actual bidi character
        assert "\u202e" not in result
        # Should contain escaped representation
        assert "\\u202e" in result

    def test_trojan_source_attack_prevention(self):
        """Test prevention of a classic trojan source attack pattern.

        The attack uses RLO (U+202E) to reverse the display order of text,
        making malicious code appear benign.
        """
        # Simulated trojan source: "malicious code" disguised as "checking"
        # The RLO character would reverse "ediM" to display as "Made"
        malicious = "check\u202eediM = True"  # displays as "check = Made"
        result = _sanitize_text(malicious)

        # The RLO character must be escaped
        assert "\u202e" not in result, "RLO must be escaped to prevent trojan source"
        assert "\\u202e" in result

        # The escaped form should make the attack visible
        assert "check" in result
        assert "ediM" in result

    def test_bidi_isolate_controls(self):
        """Test that isolate control characters (U+2066-U+2069) are escaped.

        These are newer bidi controls introduced in Unicode 6.3.
        """
        # LRI - Left-to-Right Isolate
        assert _sanitize_text("start\u2066end") == r"start\u2066end"
        # RLI - Right-to-Left Isolate
        assert _sanitize_text("start\u2067end") == r"start\u2067end"
        # FSI - First Strong Isolate
        assert _sanitize_text("start\u2068end") == r"start\u2068end"
        # PDI - Pop Directional Isolate
        assert _sanitize_text("start\u2069end") == r"start\u2069end"

    def test_bidi_embedding_controls(self):
        """Test that embedding control characters (U+202A-U+202E) are escaped.

        These are the original bidi controls that can cause display issues.
        """
        # LRE - Left-to-Right Embedding
        assert _sanitize_text("start\u202aend") == r"start\u202aend"
        # RLE - Right-to-Left Embedding
        assert _sanitize_text("start\u202bend") == r"start\u202bend"
        # PDF - Pop Directional Format
        assert _sanitize_text("start\u202cend") == r"start\u202cend"
        # LRO - Left-to-Right Override
        assert _sanitize_text("start\u202dend") == r"start\u202dend"
        # RLO - Right-to-Left Override
        assert _sanitize_text("start\u202eend") == r"start\u202eend"
