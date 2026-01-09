"""Test for issue #1225 - shell context skips Unicode spoofing character removal.

Issue #1225: In the `sanitize_for_security_context` function, when context == "shell",
the code returns early with shlex.quote() (line 181), which SKIPS the Unicode spoofing
character removal that happens later (lines 207-208):

- ZERO_WIDTH_CHARS_PATTERN.sub('', s) - Zero-width characters
- BIDI_OVERRIDE_PATTERN.sub('', s) - Bidirectional override attacks

This is a SECURITY VULNERABILITY because:
1. Unicode spoofing characters can be used for homograph attacks
2. Zero-width characters can hide malicious content
3. Bidi override characters can display text differently than interpreted

The FIX: Shell context should also remove Unicode spoofing characters before quoting.
"""

import pytest
import shlex
from flywheel.cli import sanitize_for_security_context


class TestIssue1225:
    """Test that shell context removes Unicode spoofing characters.

    The vulnerability is that shell context returns early (line 181) and skips
    the Unicode spoofing character removal (lines 207-208), allowing:
    - Zero-width characters (U+200B-U+200D, U+2060, U+FEFF)
    - Bidirectional override characters (U+202A-U+202E, U+2066-U+2069)
    """

    def test_shell_context_removes_zero_width_chars(self):
        """Test that shell context removes zero-width characters.

        Zero-width characters can hide malicious content and should be removed
        before quoting for shell usage.
        """
        # Input with zero-width characters
        zero_width_chars = [
            ("normal\u200Btext", "normaltext"),  # U+200B Zero Width Space
            ("text\u200Cwith\u200Dhidden", "textwithhidden"),  # U+200C, U+200D
            ("file\u2060name", "filename"),  # U+2060 Word Joiner
            ("text\uFEFFat_end", "textat_end"),  # U+FEFF Zero Width No-Break Space
        ]

        for input_str, expected_clean in zero_width_chars:
            result = sanitize_for_security_context(input_str, context="shell")

            # Zero-width characters should be removed before quoting
            expected = shlex.quote(expected_clean)

            assert result == expected, (
                f"Zero-width characters must be removed in shell context. "
                f"Input: '{repr(input_str)}', Expected: '{expected}', Got: '{result}'"
            )

    def test_shell_context_removes_bidi_override_chars(self):
        """Test that shell context removes bidirectional override characters.

        Bidi override characters can make text display differently than it's
        interpreted, which is a security risk.
        """
        # Input with bidirectional override characters
        bidi_chars = [
            ("left\u202Ato\u202Cright", "lefttoright"),  # LRE, PDF
            ("right\u202Eto\u202Dleft", "righttoleft"),  # RLE, PDF
            ("text\u2066with\u2069bidi", "textwithbidi"),  # LRI, PDI
        ]

        for input_str, expected_clean in bidi_chars:
            result = sanitize_for_security_context(input_str, context="shell")

            # Bidi override characters should be removed before quoting
            expected = shlex.quote(expected_clean)

            assert result == expected, (
                f"Bidi override characters must be removed in shell context. "
                f"Input: '{repr(input_str)}', Expected: '{expected}', Got: '{result}'"
            )

    def test_shell_context_combined_spoofing_chars(self):
        """Test that shell context removes all Unicode spoofing characters.

        This tests a combination of zero-width, bidi override, and control characters.
        """
        # String with multiple types of spoofing characters
        input_str = "file\u200B\u202Aname\u202C\nmalicious\uFEFF"

        result = sanitize_for_security_context(input_str, context="shell")

        # All spoofing characters should be removed
        # Expected: "filename malicious" (zero-width and bidi chars removed)
        # Then newline removed: "filename malicious"
        # Then quoted
        expected = shlex.quote("filename malicious")

        assert result == expected, (
            f"All Unicode spoofing characters must be removed. "
            f"Expected: '{expected}', Got: '{result}'"
        )

    def test_shell_context_vs_general_context_spoofing(self):
        """Test that shell and general contexts handle spoofing characters similarly.

        Both contexts should remove Unicode spoofing characters, but shell context
        should also quote the result.
        """
        input_str = "text\u200B\u202Awith\u202Cspoofing"

        general_result = sanitize_for_security_context(input_str, context="general")
        shell_result = sanitize_for_security_context(input_str, context="shell")

        # Both should remove spoofing characters
        assert "\u200B" not in general_result
        assert "\u202A" not in general_result
        assert "\u202C" not in general_result

        assert "\u200B" not in shell_result
        assert "\u202A" not in shell_result
        assert "\u202C" not in shell_result

        # Shell result should be quoted
        expected_shell = shlex.quote("textwithspoofing")
        assert shell_result == expected_shell

    def test_shell_context_normal_text_unchanged(self):
        """Test that normal text without spoofing characters works correctly."""
        normal_inputs = [
            "normal_file.txt",
            "file with spaces",
        ]

        for input_str in normal_inputs:
            result = sanitize_for_security_context(input_str, context="shell")
            expected = shlex.quote(input_str)

            assert result == expected, (
                f"Normal characters should be preserved and quoted. "
                f"Input: '{input_str}', Expected: '{expected}', Got: '{result}'"
            )
