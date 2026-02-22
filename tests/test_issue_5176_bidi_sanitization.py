"""Regression tests for Issue #5176: Bidirectional Unicode control character sanitization.

This test file ensures that bidi control characters in todo.text are properly escaped
to prevent text direction spoofing attacks.

Bidi control characters that should be escaped:
- U+202A-U+202E: Bidirectional embedding/override controls
- U+2066-U+2069: Bidirectional isolate controls
- U+200E-U+200F: Left-to-right/Right-to-left marks (LRM/RLM)
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBidiControlCharacterSanitization:
    """Tests for bidi control character sanitization."""

    def test_sanitize_text_escapes_rtl_override_u202e(self) -> None:
        """RTL Override (U+202E) should be escaped to visible representation."""
        result = _sanitize_text("\u202e")
        assert result == "\\u202e"
        assert "\u202e" not in result

    def test_sanitize_text_escapes_ltr_override_u202d(self) -> None:
        """LTR Override (U+202D) should be escaped to visible representation."""
        result = _sanitize_text("\u202d")
        assert result == "\\u202d"
        assert "\u202d" not in result

    def test_sanitize_text_escapes_bidi_embedding_u202a_u202b(self) -> None:
        """Bidi embedding controls (U+202A, U+202B) should be escaped."""
        assert _sanitize_text("\u202a") == "\\u202a"
        assert _sanitize_text("\u202b") == "\\u202b"

    def test_sanitize_text_escapes_bidi_pop_u202c(self) -> None:
        """Bidi Pop (U+202C) should be escaped."""
        assert _sanitize_text("\u202c") == "\\u202c"

    def test_sanitize_text_escapes_isolate_controls_u2066_u2069(self) -> None:
        """Bidi isolate controls (U+2066-U+2069) should be escaped."""
        assert _sanitize_text("\u2066") == "\\u2066"  # LTR isolate
        assert _sanitize_text("\u2067") == "\\u2067"  # RTL isolate
        assert _sanitize_text("\u2068") == "\\u2068"  # First strong isolate
        assert _sanitize_text("\u2069") == "\\u2069"  # Pop directional isolate

    def test_sanitize_text_escapes_lrm_rlm_u200e_u200f(self) -> None:
        """LRM/RLM marks (U+200E, U+200F) should be escaped."""
        assert _sanitize_text("\u200e") == "\\u200e"  # LRM
        assert _sanitize_text("\u200f") == "\\u200f"  # RLM

    def test_format_todo_with_rtl_override_is_escaped(self) -> None:
        """Todo with RTL override should show escaped representation."""
        # U+202E is the Right-to-Left Override character
        todo = Todo(id=1, text="exec\u202epit.txt")
        result = TodoFormatter.format_todo(todo)
        # Should show escaped representation, not the actual bidi char
        assert "\\u202e" in result
        assert "\u202e" not in result

    def test_format_todo_with_bidi_spoof_attack(self) -> None:
        """Bidi spoofing attack pattern should be neutralized."""
        # Simulate attack: "readme" followed by RTL override then "txt.pypa-"
        # This would display as "readme-pypa.txt" visually
        malicious_text = "readme\u202etxt.pypa-"
        todo = Todo(id=1, text=malicious_text)
        result = TodoFormatter.format_todo(todo)
        # The bidi char should be escaped
        assert "\\u202e" in result
        assert "\u202e" not in result

    def test_format_todo_preserves_normal_unicode(self) -> None:
        """Normal unicode characters should still pass through unchanged."""
        todo = Todo(id=1, text="Buy café and 日本語")
        result = TodoFormatter.format_todo(todo)
        assert "café" in result
        assert "日本語" in result

    def test_sanitize_text_mixed_bidi_controls(self) -> None:
        """Multiple bidi control characters should all be escaped."""
        text = "Hello\u202eWorld\u2066Test\u200e"
        result = _sanitize_text(text)
        assert "\\u202e" in result
        assert "\\u2066" in result
        assert "\\u200e" in result
        assert "\u202e" not in result
        assert "\u2066" not in result
        assert "\u200e" not in result
