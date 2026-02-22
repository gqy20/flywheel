"""Regression tests for Issue #5111: BiDi character sanitization.

Bidirectional (BiDi) Unicode characters can cause text display manipulation attacks
where the visual appearance of text differs from its logical content.

BiDi override characters:
- U+202A-U+202E: Left-to-Right Embedding, Right-to-Left Embedding,
                  Pop Directional Format, Left-to-Right Override, Right-to-Left Override
- U+2066-U+2069: Left-to-Right Isolate, Right-to-Left Isolate,
                  First Strong Isolate, Pop Directional Isolate

Example attack: 'print("Read \u202eCMD.exe\u202c")' appears visually as 'Read exe.CMD'
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBiDiCharacterSanitization:
    """Test that Unicode BiDi characters are properly escaped."""

    def test_sanitize_text_escapes_right_to_left_override_u202e(self):
        """Test that U+202E (Right-to-Left Override) is escaped."""
        # This is the most dangerous BiDi character for attacks
        result = _sanitize_text("Hello\u202eWorld")
        assert "\u202e" not in result  # Raw character should not be in output
        assert "\\u202e" in result or "\\x202e" in result or "\\x8e" in result

    def test_sanitize_text_escapes_all_bidi_override_chars_u202a_to_u202e(self):
        """Test that all BiDi override characters (U+202A-U+202E) are escaped."""
        # U+202A: Left-to-Right Embedding
        assert _sanitize_text("a\u202ab") != "a\u202ab"
        assert "\u202a" not in _sanitize_text("a\u202ab")
        # U+202B: Right-to-Left Embedding
        assert "\u202b" not in _sanitize_text("a\u202bb")
        # U+202C: Pop Directional Format
        assert "\u202c" not in _sanitize_text("a\u202cb")
        # U+202D: Left-to-Right Override
        assert "\u202d" not in _sanitize_text("a\u202db")
        # U+202E: Right-to-Left Override
        assert "\u202e" not in _sanitize_text("a\u202eb")

    def test_sanitize_text_escapes_bidi_isolate_chars_u2066_to_u2069(self):
        """Test that BiDi isolate characters (U+2066-U+2069) are escaped."""
        # U+2066: Left-to-Right Isolate
        assert "\u2066" not in _sanitize_text("a\u2066b")
        # U+2067: Right-to-Left Isolate
        assert "\u2067" not in _sanitize_text("a\u2067b")
        # U+2068: First Strong Isolate
        assert "\u2068" not in _sanitize_text("a\u2068b")
        # U+2069: Pop Directional Isolate
        assert "\u2069" not in _sanitize_text("a\u2069b")

    def test_sanitize_text_bidi_attack_example(self):
        """Test the attack example from the issue: 'Read CMD.exe' attack."""
        # Attack: "Read \u202eCMD.exe\u202c" would display as "Read exe.CMD"
        malicious = "Read \u202eCMD.exe\u202c"
        result = _sanitize_text(malicious)
        # Raw BiDi characters should not be present
        assert "\u202e" not in result
        assert "\u202c" not in result
        # The word "CMD" should appear before "exe" in the logical output
        # (escaped chars don't affect ordering)
        assert "CMD" in result
        assert "exe" in result

    def test_format_todo_escapes_bidi_chars(self):
        """Test that format_todo properly escapes BiDi characters."""
        todo = Todo(id=1, text="Buy milk\u202eFAKE", done=False)
        result = TodoFormatter.format_todo(todo)
        # Raw BiDi character should not be present
        assert "\u202e" not in result
        # Escaped representation should be present
        assert "milk" in result
        assert "FAKE" in result

    def test_sanitize_text_invisible_formatting_chars(self):
        """Test that invisible formatting characters are also escaped."""
        # U+200B: Zero Width Space
        assert "\u200b" not in _sanitize_text("a\u200bb")
        # U+200E: Left-to-Right Mark
        assert "\u200e" not in _sanitize_text("a\u200eb")
        # U+200F: Right-to-Left Mark
        assert "\u200f" not in _sanitize_text("a\u200fb")
        # U+FEFF: Byte Order Mark / Zero Width No-Break Space
        assert "\ufeff" not in _sanitize_text("a\ufeffb")

    def test_sanitize_text_normal_unicode_unchanged(self):
        """Test that normal Unicode text is not affected."""
        # These should pass through unchanged
        assert _sanitize_text("café") == "café"
        assert _sanitize_text("日本語") == "日本語"
        assert _sanitize_text("🎉") == "🎉"
        # Regular text without BiDi
        assert _sanitize_text("Hello World") == "Hello World"

    def test_sanitize_text_bidi_with_other_controls(self):
        """Test that BiDi chars are escaped alongside other control characters."""
        # Mix of BiDi and C0 control characters
        result = _sanitize_text("a\u202e\nb\tc")
        assert "\u202e" not in result
        assert "\n" not in result
        assert "\t" not in result
        assert "\\n" in result
        assert "\\t" in result
