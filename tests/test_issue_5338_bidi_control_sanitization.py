"""Tests for Bidi Unicode control character sanitization (Issue #5338).

Bidi (bidirectional) Unicode control characters can be used for text direction
spoofing attacks. These characters should be sanitized to prevent security issues.

Bidi control character ranges:
- U+200E-U+200F: LRM (Left-to-Right Mark), RLM (Right-to-Left Mark)
- U+202A-U+202E: LRE, RLE, PDF, LRO, RLO (embedding and override controls)
- U+2066-U+2069: LRI, RLI, FSI, PDI (isolate controls)
"""

from flywheel.formatter import _sanitize_text


class TestBidiControlSanitization:
    """Test that Bidi control characters are properly escaped."""

    def test_sanitize_text_escapes_lrm_rlm(self):
        """Test that LRM (U+200E) and RLM (U+200F) are escaped."""
        # LRM - Left-to-Right Mark
        assert _sanitize_text("hello\u200eworld") == r"hello\u200eworld"
        # RLM - Right-to-Left Mark
        assert _sanitize_text("hello\u200fworld") == r"hello\u200fworld"

    def test_sanitize_text_escapes_embedding_overrides(self):
        """Test that embedding and override controls (U+202A-U+202E) are escaped."""
        # LRE - Left-to-Right Embedding (U+202A)
        assert _sanitize_text("text\u202aend") == r"text\u202aend"
        # RLE - Right-to-Left Embedding (U+202B)
        assert _sanitize_text("text\u202bend") == r"text\u202bend"
        # PDF - Pop Directional Format (U+202C)
        assert _sanitize_text("text\u202cend") == r"text\u202cend"
        # LRO - Left-to-Right Override (U+202D)
        assert _sanitize_text("text\u202dend") == r"text\u202dend"
        # RLO - Right-to-Left Override (U+202E) - critical for spoofing attacks
        assert _sanitize_text("hello\u202eworld") == r"hello\u202eworld"

    def test_sanitize_text_escapes_isolate_controls(self):
        """Test that isolate controls (U+2066-U+2069) are escaped."""
        # LRI - Left-to-Right Isolate (U+2066)
        assert _sanitize_text("text\u2066end") == r"text\u2066end"
        # RLI - Right-to-Left Isolate (U+2067)
        assert _sanitize_text("text\u2067end") == r"text\u2067end"
        # FSI - First Strong Isolate (U+2068)
        assert _sanitize_text("text\u2068end") == r"text\u2068end"
        # PDI - Pop Directional Isolate (U+2069)
        assert _sanitize_text("text\u2069end") == r"text\u2069end"

    def test_sanitize_text_escapes_rtl_override_attack_vector(self):
        """Test that RLO (U+202E) attack vector is neutralized.

        RLO can be used to display text backwards, e.g.:
        "Click here\u202eelga.exe" would display as "Click hereexe.agle"
        """
        # Simulated attack: making "exe.php" look like "exe.txt"
        attack_string = "readme\u202etxt.exe"
        result = _sanitize_text(attack_string)
        assert "\\u202e" in result
        assert result == r"readme\u202etxt.exe"

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes Bidi control characters."""
        from flywheel.formatter import TodoFormatter
        from flywheel.todo import Todo

        todo = Todo(id=1, text="Buy milk\u202e", done=False)
        result = TodoFormatter.format_todo(todo)
        assert result == r"[ ]   1 Buy milk\u202e"

    def test_bidi_with_other_controls(self):
        """Test that Bidi chars are escaped alongside other control characters."""
        # Mix of C0, C1, DEL, and Bidi controls
        assert _sanitize_text("a\x01b\u202ec\x7fd") == r"a\x01b\u202ec\x7fd"

    def test_bidi_multiple_chars(self):
        """Test multiple Bidi characters in sequence."""
        assert _sanitize_text("\u202a\u202b\u202e") == r"\u202a\u202b\u202e"
        assert _sanitize_text("\u2066\u2067\u2068\u2069") == r"\u2066\u2067\u2068\u2069"

    def test_existing_unicode_still_passes(self):
        """Test that valid non-Bidi Unicode still passes through unchanged."""
        # Japanese characters (should not be affected)
        assert _sanitize_text("こんにちは") == "こんにちは"
        # Euro sign (should not be affected - near the Bidi range but not Bidi)
        assert _sanitize_text("€") == "€"
        # Regular text
        assert _sanitize_text("Hello World") == "Hello World"
