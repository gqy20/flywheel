"""Tests for BIDI control character sanitization (Issue #6078).

BIDI (Bi-Directional Text) control characters can visually reverse or
manipulate text direction, enabling text direction spoofing attacks.
These characters should be sanitized to prevent security vulnerabilities.

BIDI character ranges:
- U+200E: Left-to-Right Mark (LRM)
- U+200F: Right-to-Left Mark (RLM)
- U+202A-U+202E: Embedding/Override (LRE, RLE, PDF, LRO, RLO)
- U+2066-U+2069: Isolates (LRI, RLI, FSI, PDI)
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBIDIControlSanitization:
    """Test that BIDI control characters are properly escaped."""

    def test_sanitize_rtl_override_u202e(self) -> None:
        """U+202E (RLO - Right-to-Left Override) should be escaped.

        This is the most dangerous BIDI character as it can completely
        reverse the visual order of following text.
        """
        result = _sanitize_text("\u202eABC")
        assert result == r"\u202eABC"
        assert "\u202e" not in result

    def test_sanitize_ltr_embedding_u202a(self) -> None:
        """U+202A (LRE - Left-to-Right Embedding) should be escaped."""
        result = _sanitize_text("\u202atest")
        assert result == r"\u202atest"
        assert "\u202a" not in result

    def test_sanitize_rtl_embedding_u202b(self) -> None:
        """U+202B (RLE - Right-to-Left Embedding) should be escaped."""
        result = _sanitize_text("\u202btext")
        assert result == r"\u202btext"
        assert "\u202b" not in result

    def test_sanitize_pop_directional_format_u202c(self) -> None:
        """U+202C (PDF - Pop Directional Format) should be escaped."""
        result = _sanitize_text("\u202cend")
        assert result == r"\u202cend"
        assert "\u202c" not in result

    def test_sanitize_ltr_override_u202d(self) -> None:
        """U+202D (LRO - Left-to-Right Override) should be escaped."""
        result = _sanitize_text("\u202dtext")
        assert result == r"\u202dtext"
        assert "\u202d" not in result

    def test_sanitize_ltr_isolate_u2066(self) -> None:
        """U+2066 (LRI - Left-to-Right Isolate) should be escaped."""
        result = _sanitize_text("\u2066text\u2069")
        assert result == r"\u2066text\u2069"
        assert "\u2066" not in result
        assert "\u2069" not in result

    def test_sanitize_rtl_isolate_u2067(self) -> None:
        """U+2067 (RLI - Right-to-Left Isolate) should be escaped."""
        result = _sanitize_text("\u2067content")
        assert result == r"\u2067content"
        assert "\u2067" not in result

    def test_sanitize_first_strong_isolate_u2068(self) -> None:
        """U+2068 (FSI - First Strong Isolate) should be escaped."""
        result = _sanitize_text("\u2068data")
        assert result == r"\u2068data"
        assert "\u2068" not in result

    def test_sanitize_pop_directional_isolate_u2069(self) -> None:
        """U+2069 (PDI - Pop Directional Isolate) should be escaped."""
        result = _sanitize_text("text\u2069")
        assert result == r"text\u2069"
        assert "\u2069" not in result

    def test_sanitize_ltr_mark_u200e(self) -> None:
        """U+200E (LRM - Left-to-Right Mark) should be escaped."""
        result = _sanitize_text("a\u200eb")
        assert result == r"a\u200eb"
        assert "\u200e" not in result

    def test_sanitize_rtl_mark_u200f(self) -> None:
        """U+200F (RLM - Right-to-Left Mark) should be escaped."""
        result = _sanitize_text("a\u200fb")
        assert result == r"a\u200fb"
        assert "\u200f" not in result

    def test_all_bidi_ranges_escaped(self) -> None:
        """All BIDI control characters should be escaped."""
        bidi_chars = [
            "\u200e",  # LRM
            "\u200f",  # RLM
            "\u202a",  # LRE
            "\u202b",  # RLE
            "\u202c",  # PDF
            "\u202d",  # LRO
            "\u202e",  # RLO
            "\u2066",  # LRI
            "\u2067",  # RLI
            "\u2068",  # FSI
            "\u2069",  # PDI
        ]
        for char in bidi_chars:
            result = _sanitize_text(char)
            # Should contain escaped representation
            assert "\\u" in result, f"BIDI char {hex(ord(char))} not escaped"
            # Should not contain actual BIDI character
            assert char not in result, f"BIDI char {hex(ord(char))} still present"

    def test_sanitize_bidi_spoofing_attack_vector(self) -> None:
        """Test a realistic BIDI spoofing attack scenario.

        An attacker might try to display "SafeFile.exe" but hide
        dangerous content using RLO to display as "exe.elifFecaS" or
        make it look like a different file extension.
        """
        # RLO attack: "txt.exe" with RLO could appear as "exe.txt"
        malicious = "txt\u202eexe."  # With RLO, visually appears reversed
        result = _sanitize_text(malicious)
        assert result == r"txt\u202eexe."
        assert "\u202e" not in result

    def test_format_todo_escapes_bidi(self) -> None:
        """TodoFormatter should properly escape BIDI characters in todo text."""
        todo = Todo(id=1, text="Hello\u202eWorld", done=False)
        result = TodoFormatter.format_todo(todo)
        assert "\\u202e" in result
        assert "\u202e" not in result
        assert result == r"[ ]   1 Hello\u202eWorld"

    def test_bidi_with_other_control_chars(self) -> None:
        """BIDI chars mixed with other control chars should all be escaped."""
        # Mix of BIDI, C0, and DEL
        result = _sanitize_text("a\u202e\x01\u200f\x7f")
        assert result == r"a\u202e\x01\u200f\x7f"
        assert "\u202e" not in result
        assert "\u200f" not in result
        assert "\x01" not in result
        assert "\x7f" not in result

    def test_bidi_escape_format_is_unicode(self) -> None:
        """BIDI characters should use \\uXXXX format for consistency."""
        result = _sanitize_text("\u202e")
        assert result == r"\u202e"
        # Verify it's exactly the right format (6 chars: \ u 2 0 2 e)
        assert len(result) == 6
