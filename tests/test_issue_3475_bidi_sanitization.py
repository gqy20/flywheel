"""Regression tests for Issue #3475: BIDI control character sanitization.

BIDI (bidirectional) control characters can be used to visually reorder text,
enabling text direction spoofing attacks where malicious content appears
benign. These tests ensure BIDI characters are escaped to visible representations.

BIDI ranges covered:
- U+200E-U+200F: LRM (Left-to-Right Mark), RLM (Right-to-Left Mark)
- U+202A-U+202E: LRE, RLE, PDF, LRO, RLO
- U+2066-U+2069: LRI, RLI, FSI, PDI
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBIDICharacterSanitization:
    """Test that BIDI control characters are properly escaped."""

    # U+202A-U+202E range (LRE, RLE, PDF, LRO, RLO)

    def test_sanitize_rlo_character(self):
        """Test that RLO (Right-to-Left Override, U+202E) is escaped."""
        # RLO can reverse text direction, hiding malicious content
        assert _sanitize_text("\u202e") == r"\u202e"
        assert _sanitize_text("Hello\u202eWorld") == r"Hello\u202eWorld"

    def test_sanitize_lro_character(self):
        """Test that LRO (Left-to-Right Override, U+202D) is escaped."""
        assert _sanitize_text("\u202d") == r"\u202d"
        assert _sanitize_text("Text\u202dMore") == r"Text\u202dMore"

    def test_sanitize_lre_character(self):
        """Test that LRE (Left-to-Right Embedding, U+202A) is escaped."""
        assert _sanitize_text("\u202a") == r"\u202a"
        assert _sanitize_text("A\u202aB") == r"A\u202aB"

    def test_sanitize_rle_character(self):
        """Test that RLE (Right-to-Left Embedding, U+202B) is escaped."""
        assert _sanitize_text("\u202b") == r"\u202b"
        assert _sanitize_text("X\u202bY") == r"X\u202bY"

    def test_sanitize_pdf_character(self):
        """Test that PDF (Pop Directional Format, U+202C) is escaped."""
        assert _sanitize_text("\u202c") == r"\u202c"
        assert _sanitize_text("End\u202c") == r"End\u202c"

    # U+2066-U+2069 range (LRI, RLI, FSI, PDI)

    def test_sanitize_lri_character(self):
        """Test that LRI (Left-to-Right Isolate, U+2066) is escaped."""
        assert _sanitize_text("\u2066") == r"\u2066"
        assert _sanitize_text("Isolate\u2066Text") == r"Isolate\u2066Text"

    def test_sanitize_rli_character(self):
        """Test that RLI (Right-to-Left Isolate, U+2067) is escaped."""
        assert _sanitize_text("\u2067") == r"\u2067"
        assert _sanitize_text("RLI\u2067Here") == r"RLI\u2067Here"

    def test_sanitize_fsi_character(self):
        """Test that FSI (First Strong Isolate, U+2068) is escaped."""
        assert _sanitize_text("\u2068") == r"\u2068"
        assert _sanitize_text("FSI\u2068Test") == r"FSI\u2068Test"

    def test_sanitize_pdi_character(self):
        """Test that PDI (Pop Directional Isolate, U+2069) is escaped."""
        assert _sanitize_text("\u2069") == r"\u2069"
        assert _sanitize_text("PDI\u2069End") == r"PDI\u2069End"

    # U+200E-U+200F range (LRM, RLM)

    def test_sanitize_lrm_character(self):
        """Test that LRM (Left-to-Right Mark, U+200E) is escaped."""
        assert _sanitize_text("\u200e") == r"\u200e"
        assert _sanitize_text("LRM\u200eMark") == r"LRM\u200eMark"

    def test_sanitize_rlm_character(self):
        """Test that RLM (Right-to-Left Mark, U+200F) is escaped."""
        assert _sanitize_text("\u200f") == r"\u200f"
        assert _sanitize_text("RLM\u200fHere") == r"RLM\u200fHere"


class TestBIDIAttackExamples:
    """Test real-world BIDI attack patterns."""

    def test_bidi_attack_example_hello_abcd_exe(self):
        """Test the classic 'Hello[DCBA].exe' spoofing attack.

        The string 'Hello\u202eDCBA.exe' visually appears as 'Helloexe.ABCD'
        which could trick users into running a malicious executable.
        After sanitization, the RLO character should be visible.
        """
        # The attack string: "Hello" + RLO + "DCBA.exe"
        attack_string = "Hello\u202eDCBA.exe"
        sanitized = _sanitize_text(attack_string)
        # The RLO should be escaped, making the attack visible
        assert "\u202e" not in sanitized
        assert r"\u202e" in sanitized
        # The literal text should be preserved
        assert "Hello" in sanitized
        assert "DCBA.exe" in sanitized

    def test_combined_bidi_with_control_chars(self):
        """Test that BIDI chars are sanitized alongside other control chars."""
        # Mix of BIDI, C0 controls, and C1 controls
        combined = "Start\u202e\x1b\x80End"
        sanitized = _sanitize_text(combined)
        # All should be escaped
        assert r"\u202e" in sanitized  # BIDI RLO
        assert r"\x1b" in sanitized  # ESC
        assert r"\x80" in sanitized  # C1 control
        assert "\u202e" not in sanitized  # Raw BIDI removed
        assert "\x1b" not in sanitized  # Raw ESC removed
        assert "\x80" not in sanitized  # Raw C1 removed

    def test_multiple_bidi_chars_in_sequence(self):
        """Test multiple BIDI characters in sequence are all escaped."""
        text = "\u202a\u202b\u202c\u202d\u202e"
        sanitized = _sanitize_text(text)
        assert sanitized == r"\u202a\u202b\u202c\u202d\u202e"

    def test_bidi_isolate_chars_sequence(self):
        """Test isolate BIDI characters in sequence are all escaped."""
        text = "\u2066\u2067\u2068\u2069"
        sanitized = _sanitize_text(text)
        assert sanitized == r"\u2066\u2067\u2068\u2069"

    def test_mixed_bidi_ranges(self):
        """Test BIDI chars from all ranges together."""
        text = "\u200e\u200f\u202a\u202e\u2066\u2069"
        sanitized = _sanitize_text(text)
        assert sanitized == r"\u200e\u200f\u202a\u202e\u2066\u2069"


class TestBIDIWithTodoFormatter:
    """Test BIDI sanitization through TodoFormatter."""

    def test_format_todo_escapes_rlo(self):
        """Test that TodoFormatter escapes RLO in todo text."""
        todo = Todo(id=1, text="Task\u202eMalicious", done=False)
        result = TodoFormatter.format_todo(todo)
        assert r"\u202e" in result
        assert "\u202e" not in result

    def test_format_list_escapes_bidi(self):
        """Test that format_list properly escapes BIDI chars."""
        todos = [
            Todo(id=1, text="Normal task"),
            Todo(id=2, text="Attack\u202eDCBA.exe"),
        ]
        result = TodoFormatter.format_list(todos)
        lines = result.split("\n")
        assert len(lines) == 2
        assert r"\u202e" in lines[1]
        assert "\u202e" not in result
