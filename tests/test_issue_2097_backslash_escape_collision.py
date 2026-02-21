"""Regression tests for Issue #2097: Backslash escape collision with sanitized control characters.

This test file ensures that literal backslash-escape text in user input is
distinguishable from sanitized control characters to prevent escape sequence
collision attacks.

The vulnerability occurs when:
1. User inputs literal text like r"\x01" (6 characters: backslash, x, 0, 1)
2. Actual control char "\x01" (1 character) is sanitized to r"\x01"
3. Both produce identical output, creating ambiguity

Solution: Escape backslash character BEFORE escaping control characters.
"""

from __future__ import annotations

from flywheel.formatter import TodoFormatter, _sanitize_text
from flywheel.todo import Todo


class TestBackslashEscapeCollision:
    """Test that literal backslash text doesn't collide with sanitized control chars."""

    def test_control_char_vs_literal_backslash_x_collision(self):
        """Actual control char and literal backslash-x text must produce different outputs.

        This is the core vulnerability: "\x01" (control char) and r"\x01" (literal text)
        currently produce identical output, making them indistinguishable.
        """
        # Actual control character (SOH - Start of Header)
        actual_control_char_output = _sanitize_text("\x01")

        # Literal backslash-x-zero-one text (6 characters: \, x, 0, 1)
        literal_backslash_text_output = _sanitize_text(r"\x01")

        # These MUST be different to prevent collision attacks
        assert actual_control_char_output != literal_backslash_text_output, (
            "SECURITY: Control character and literal backslash text produced identical output! "
            "This creates an escape sequence collision vulnerability."
        )

    def test_single_backslash_is_escaped(self):
        """A single backslash character should be escaped to double backslash.

        Input: "\" (1 character)
        Output: r"\\" (2 characters: backslash, backslash)
        """
        result = _sanitize_text("\\")
        assert result == r"\\", f"Expected r'\\\\' but got {result!r}"
        # Verify it's actually 2 characters, not 1
        assert len(result) == 2, f"Escaped backslash should be 2 chars, got {len(result)}"

    def test_literal_newline_text_vs_actual_newline(self):
        """Literal r"\\n" text must be distinguishable from actual newline character.

        After fixing:
        - Input "\n" (actual newline) → r"\\n" (escaped backslash + n)
        - Input r"\n" (literal text) → r"\\n" (escaped backslash + n)

        Wait, this is still a collision! The fix needs more thought...

        Actually, after escaping backslash FIRST:
        - Input "\n" (actual newline) → r"\\n" (the \n replacement)
        - Input r"\n" (literal) → r"\\n" (backslash becomes \\, n stays n)

        Hmm, this is still tricky. Let me reconsider...

        With the fix (escape backslash first):
        Step 1: Escape backslashes
        - Input "\n" → "\n" (no backslash to escape)
        - Input r"\n" → "\\n" (backslash becomes \\)

        Step 2: Escape control characters
        - Input "\n" → "\\n" (newline becomes \n)
        - Input "\\n" → "\\n" (backslash already escaped, no control chars)

        So after BOTH steps:
        - Actual newline "\n" → r"\n" (2 chars)
        - Literal r"\n" → r"\\n" (3 chars)

        This should work! Let me write the test correctly.
        """
        # Actual newline character (1 char)
        actual_newline_output = _sanitize_text("\n")

        # Literal backslash-n text (2 characters: backslash, n)
        literal_newline_output = _sanitize_text(r"\n")

        # These MUST be different
        assert actual_newline_output != literal_newline_output, (
            "SECURITY: Actual newline and literal \\n text produced identical output!"
        )

        # Actual newline should be r"\n" (2 chars via replacement list)
        assert actual_newline_output == r"\n", f"Expected r'\\n' but got {actual_newline_output!r}"

        # Literal text should be r"\\n" (3 chars: escaped backslash + n)
        assert literal_newline_output == r"\\n", f"Expected r'\\\\n' but got {literal_newline_output!r}"

    def test_normal_text_with_backslashes(self):
        """Normal text containing backslashes should have them escaped."""
        # Windows-style path
        result = _sanitize_text(r"C:\Users\test\file.txt")
        assert result == r"C:\\Users\\test\\file.txt"

        # Multiple consecutive backslashes
        result = _sanitize_text(r"\\\\server\\share")
        assert result == r"\\\\\\\\server\\\\share"

    def test_backslash_followed_by_control_char(self):
        """Input with both backslash and control character should escape both properly."""
        # Backslash followed by SOH control char
        result = _sanitize_text("\\\x01")

        # Backslash should be escaped to \\
        # Control char \x01 should be escaped to \x01
        # Result should be r"\\\x01" (4 chars: \\, \, x, 0, 1)
        assert result == r"\\\x01", f"Expected r'\\\\\\x01' but got {result!r}"

    def test_mixed_backslashes_and_various_control_chars(self):
        """Complex input with backslashes and multiple control characters."""
        # Literal r"\x" followed by actual control chars
        result = _sanitize_text(r"literal\x" + "\x01\x02\x1b")

        # r"literal\x" → r"literal\\x" (backslash escaped)
        # "\x01\x02\x1b" → r"\x01\x02\x1b" (control chars escaped)
        # Combined: r"literal\\x\x01\x02\x1b"
        assert result == r"literal\\x\x01\x02\x1b"

    def test_format_todo_with_backslash_in_text(self):
        """TodoFormatter should properly escape backslashes in todo text."""
        todo = Todo(id=1, text=r"C:\path\to\file", done=False)
        result = TodoFormatter.format_todo(todo)

        # Backslashes should be escaped (with priority symbol)
        assert result == r"[ ] -   1 C:\\path\\to\\file"

    def test_empty_string(self):
        """Empty string should remain empty."""
        assert _sanitize_text("") == ""

    def test_only_backslashes(self):
        """String of only backslashes should all be escaped."""
        assert _sanitize_text("\\") == r"\\"
        assert _sanitize_text("\\\\") == r"\\\\"
        assert _sanitize_text("\\\\\\\\") == r"\\\\\\\\"

    def test_backslash_collision_attack_vector(self):
        """Test a potential attack vector where user tries to mimic control char output.

        An attacker might input literal text that LOOKS like sanitized control chars.
        After the fix, these should be distinguishable.
        """
        # Attacker inputs literal text that looks like escape sequences
        malicious_literal_input = r"\x01\n\x1b[31m"

        # Actual control characters
        actual_control_chars = "\x01\n\x1b[31m"

        literal_output = _sanitize_text(malicious_literal_input)
        control_output = _sanitize_text(actual_control_chars)

        # Must be distinguishable
        assert literal_output != control_output, (
            "SECURITY: Attack succeeded - literal text mimics control char output!"
        )

        # Literal input should have backslashes escaped
        assert literal_output == r"\\x01\\n\\x1b[31m"

        # Control chars should be escaped normally
        assert control_output == r"\x01\n\x1b[31m"


class TestBackslashEscapeComprehensive:
    """Comprehensive tests for backslash escaping behavior."""

    def test_all_common_escape_sequences_distinguishable(self):
        """Ensure common escape sequences are distinguishable from literal text."""
        test_cases = [
            ("\n", r"\n"),  # newline
            ("\r", r"\r"),  # carriage return
            ("\t", r"\t"),  # tab
            ("\x00", r"\x00"),  # null
            ("\x1b", r"\x1b"),  # escape
            ("\x7f", r"\x7f"),  # DEL
            ("\x80", r"\x80"),  # PAD (C1)
            ("\x9f", r"\x9f"),  # APC (C1)
        ]

        for control_char, expected_escaped in test_cases:
            # Test actual control character
            control_output = _sanitize_text(control_char)
            assert control_output == expected_escaped, (
                f"Control char {control_char!r} should escape to {expected_escaped!r}, "
                f"got {control_output!r}"
            )

            # Test literal text (backslash-escape sequence)
            literal_input = expected_escaped  # This is the literal text
            literal_output = _sanitize_text(literal_input)

            # After escaping backslash, literal should have one more backslash
            expected_literal = "\\" + expected_escaped
            assert literal_output == expected_literal, (
                f"Literal text {literal_input!r} should escape to {expected_literal!r}, "
                f"got {literal_output!r}"
            )

            # Most importantly: they must be different
            assert control_output != literal_output, (
                f"SECURITY: Control char {control_char!r} and literal {literal_input!r} "
                f"produced identical output!"
            )
