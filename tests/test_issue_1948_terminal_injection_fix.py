"""Regression test for Issue #1948: Terminal injection via control characters.

This test file ensures that control characters in todo.text are properly sanitized
to prevent terminal injection attacks via ANSI escape sequences or newline/carriage
return attacks.

Security vulnerability: Control characters in todo.text are not sanitized, allowing
terminal injection via ANSI escape sequences or newline/carriage return attacks.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestIssue1948ControlCharacterSanitization:
    """Test suite for Issue #1948: Terminal injection via control characters."""

    def test_newline_injection_attack(self):
        """Newline character should be escaped to prevent fake todo injection."""
        # Attack: Create todo with newline to fake additional todos
        todo = Todo(id=1, text="Buy milk\n[x] FAKE_DONE_TODO")
        result = TodoFormatter.format_todo(todo)

        # Should contain escaped representation, not actual newline
        assert "\\n" in result
        # Should NOT contain actual newline character
        assert "\n" not in result
        # Should render as single line
        assert result == "[ ]   1 Buy milk\\n[x] FAKE_DONE_TODO"

    def test_carriage_return_injection_attack(self):
        """Carriage return should be escaped to prevent output overwrite."""
        # Attack: Use carriage return to overwrite line start
        todo = Todo(id=1, text="Valid task\r[!] FAKE_ALERT")
        result = TodoFormatter.format_todo(todo)

        # Should contain escaped representation
        assert "\\r" in result
        # Should NOT contain actual carriage return
        assert "\r" not in result

    def test_ansi_escape_sequence_injection(self):
        """ANSI escape sequences should be escaped to prevent terminal manipulation."""
        # Attack: Use ANSI codes to hide/change text or colors
        todo = Todo(id=1, text="\x1b[31mRed Text\x1b[0m Normal")
        result = TodoFormatter.format_todo(todo)

        # Should contain escaped representation
        assert "\\x1b" in result
        # Should NOT contain actual ESC character
        assert "\x1b" not in result

    def test_tab_character_sanitization(self):
        """Tab character should be escaped visibly."""
        todo = Todo(id=1, text="Task\twith\ttabs")
        result = TodoFormatter.format_todo(todo)

        # Should contain escaped representation
        assert "\\t" in result
        # Should NOT contain actual tab character
        assert "\t" not in result

    def test_null_byte_sanitization(self):
        """Null byte should be escaped."""
        todo = Todo(id=1, text="Before\x00After")
        result = TodoFormatter.format_todo(todo)

        # Should contain escaped representation
        assert "\\x00" in result
        # Should NOT contain actual null byte
        assert "\x00" not in result

    def test_combined_attack_vector(self):
        """Combined control characters attack should all be escaped."""
        # Attack: Multiple control characters
        todo = Todo(id=1, text="Line1\nLine2\rTab\tHere\x1b[31m")
        result = TodoFormatter.format_todo(todo)

        # All should be escaped
        assert "\\n" in result
        assert "\\r" in result
        assert "\\t" in result
        assert "\\x1b" in result
        # Should NOT contain actual control characters
        assert "\n" not in result
        assert "\r" not in result
        assert "\t" not in result
        assert "\x1b" not in result

    def test_normal_text_unaffected(self):
        """Normal text without control characters should be unchanged."""
        todo = Todo(id=1, text="Buy groceries")
        result = TodoFormatter.format_todo(todo)
        assert result == "[ ]   1 Buy groceries"

    def test_sanitize_text_function_directly(self):
        """Test _sanitize_text function directly for specific control chars."""
        # Test newline
        assert _sanitize_text("test\n") == r"test\n"
        # Test carriage return
        assert _sanitize_text("test\r") == r"test\r"
        # Test tab
        assert _sanitize_text("test\t") == r"test\t"
        # Test null byte
        assert _sanitize_text("test\x00") == r"test\x00"
        # Test ANSI escape
        assert _sanitize_text("\x1b[31m") == r"\x1b[31m"

    def test_c1_control_characters(self):
        """C1 control characters (0x80-0x9f) should also be escaped."""
        # Test various C1 control characters
        for code in [0x80, 0x85, 0x90, 0x9f]:
            char = chr(code)
            result = _sanitize_text(f"test{char}")
            # Should be escaped as \xNN
            assert f"\\x{code:02x}" in result
            # Should NOT contain actual control character
            assert char not in result

    def test_del_character(self):
        """DEL character (0x7f) should be escaped."""
        todo = Todo(id=1, text="test\x7f")
        result = TodoFormatter.format_todo(todo)
        assert "\\x7f" in result
        assert "\x7f" not in result

    def test_format_list_with_control_characters(self):
        """List format should sanitize all todos properly."""
        todos = [
            Todo(id=1, text="Task 1\nFake task"),
            Todo(id=2, text="Task 2\tTabbed"),
            Todo(id=3, text="Normal task"),
        ]
        result = TodoFormatter.format_list(todos)
        lines = result.split("\n")

        # Should have 3 lines (one per todo)
        assert len(lines) == 3
        # Control characters should be escaped
        assert "\\n" in lines[0]
        assert "\\t" in lines[1]
        # Normal task should be unchanged
        assert "Normal task" in lines[2]
