"""Regression tests for Issue #5176: Bidirectional (bidi) Unicode control character sanitization.

This test file ensures that bidi control characters in todo.text are properly escaped
to prevent text direction spoofing attacks (CVE-like security issue).

Bidi control characters that must be sanitized:
- U+202A-U+202E: Bidi embedding/override controls (LRE, RLE, PDF, LRO, RLO)
- U+2066-U+2069: Isolate controls (LRI, RLI, FSI, PDI)
- U+200E-U+200F: LRM/RLM (Left-to-Right Mark, Right-to-Left Mark)
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBidiControlCharacterSanitization:
    """Tests for bidi control character sanitization."""

    def test_sanitize_text_escapes_rtl_override_u202e(self) -> None:
        """RTL Override (U+202E) should be escaped to visible representation."""
        # U+202E is the Right-to-Left Override, commonly used in spoofing attacks
        result = _sanitize_text("\u202e")
        assert result == "\\u202e"
        assert "\u202e" not in result

    def test_sanitize_text_escapes_ltr_override_u202d(self) -> None:
        """LTR Override (U+202D) should be escaped to visible representation."""
        result = _sanitize_text("\u202d")
        assert result == "\\u202d"
        assert "\u202d" not in result

    def test_sanitize_text_escapes_bidi_embedding_controls(self) -> None:
        """Bidi embedding controls (U+202A-U+202C) should be escaped."""
        # LRE (Left-to-Right Embedding)
        result = _sanitize_text("\u202a")
        assert result == "\\u202a"
        # RLE (Right-to-Left Embedding)
        result = _sanitize_text("\u202b")
        assert result == "\\u202b"
        # PDF (Pop Directional Format)
        result = _sanitize_text("\u202c")
        assert result == "\\u202c"

    def test_sanitize_text_escapes_isolate_controls(self) -> None:
        """Isolate controls (U+2066-U+2069) should be escaped."""
        # LRI (Left-to-Right Isolate)
        result = _sanitize_text("\u2066")
        assert result == "\\u2066"
        # RLI (Right-to-Left Isolate)
        result = _sanitize_text("\u2067")
        assert result == "\\u2067"
        # FSI (First Strong Isolate)
        result = _sanitize_text("\u2068")
        assert result == "\\u2068"
        # PDI (Pop Directional Isolate)
        result = _sanitize_text("\u2069")
        assert result == "\\u2069"

    def test_sanitize_text_escapes_lrm_rlm(self) -> None:
        """LRM/RLM (U+200E-U+200F) should be escaped."""
        # LRM (Left-to-Right Mark)
        result = _sanitize_text("\u200e")
        assert result == "\\u200e"
        # RLM (Right-to-Left Mark)
        result = _sanitize_text("\u200f")
        assert result == "\\u200f"

    def test_format_todo_escapes_rtl_override_in_spoofing_attack(self) -> None:
        """Real-world attack: 'exe\u202etxt' should show escaped, not appear as 'txt.exe'."""
        # This is a classic spoofing attack: "exe" + RLO + "txt" displays as "txt.exe"
        todo = Todo(id=1, text="malware\u202etxt")
        result = TodoFormatter.format_todo(todo)
        # Should contain escaped representation
        assert "\\u202e" in result
        # Should not contain actual RLO character
        assert "\u202e" not in result
        # Should show the true content, not the spoofed display
        assert "malware\\u202etxt" in result

    def test_format_todo_with_multiple_bidi_chars(self) -> None:
        """Multiple bidi control characters should all be escaped."""
        # String with multiple bidi controls
        todo = Todo(id=1, text="start\u202e\u2067middle\u200fend")
        result = TodoFormatter.format_todo(todo)
        assert "\\u202e" in result
        assert "\\u2067" in result
        assert "\\u200f" in result
        # No actual bidi chars should remain
        assert "\u202e" not in result
        assert "\u2067" not in result
        assert "\u200f" not in result

    def test_normal_unicode_still_passes_through(self) -> None:
        """Normal unicode (not bidi controls) should still pass through unchanged."""
        todo = Todo(id=1, text="Buy café and 日本語")
        result = TodoFormatter.format_todo(todo)
        assert "café" in result
        assert "日本語" in result
        # Should not contain any escape sequences
        assert "\\u" not in result


class TestBidiSanitizationEdgeCases:
    """Edge case tests for bidi control character sanitization."""

    def test_sanitize_text_empty_string(self) -> None:
        """Empty string should remain empty."""
        result = _sanitize_text("")
        assert result == ""

    def test_sanitize_text_only_bidi_chars(self) -> None:
        """String with only bidi chars should be fully escaped."""
        result = _sanitize_text("\u202a\u202b\u202c\u202d\u202e")
        assert result == "\\u202a\\u202b\\u202c\\u202d\\u202e"

    def test_sanitize_text_mixed_ascii_and_bidi(self) -> None:
        """Mixed ASCII and bidi chars should preserve ASCII, escape bidi."""
        result = _sanitize_text("hello\u202eworld")
        assert result == "hello\\u202eworld"

    def test_sanitize_text_preserves_normal_text(self) -> None:
        """Normal text without control chars should be unchanged."""
        result = _sanitize_text("Normal text with spaces and punctuation!")
        assert result == "Normal text with spaces and punctuation!"

    def test_format_list_with_bidi_spoofing_todos(self) -> None:
        """Multiple todos with bidi spoofing should each be sanitized."""
        todos = [
            Todo(id=1, text="safe\u202edanger"),
            Todo(id=2, text="\u2066isolated\u2069"),
            Todo(id=3, text="Normal task"),
        ]
        result = TodoFormatter.format_list(todos)
        lines = result.split("\n")
        assert len(lines) == 3
        assert "\\u202e" in lines[0]
        assert "\\u2066" in lines[1]
        assert "\\u2069" in lines[1]
        assert "Normal task" in lines[2]
