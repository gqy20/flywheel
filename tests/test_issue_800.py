"""Tests for Issue #800 - unicodedata.name(char) ValueError handling.

This test verifies that control characters and other characters that raise
ValueError in unicodedata.name() are properly filtered out.

The fix was implemented in Issue #794, which added proper ValueError handling
in the is_latin_script() function.
"""

import pytest
from flywheel.cli import sanitize_string


class TestIssue800:
    """Test cases for Issue #800 - ValueError from unicodedata.name()."""

    def test_control_characters_are_removed(self):
        """Test that control characters (which raise ValueError) are removed."""
        # Test common control characters that don't have Unicode names
        test_cases = [
            ("\x00Hello", "Hello"),  # Null character
            ("\x01World", "World"),  # Start of heading
            ("\x02Test", "Test"),    # Start of text
            ("\x07Alert", "Alert"),  # Bell
            ("\x08Back", "Back"),    # Backspace
            ("\x0bLine", "Line"),    # Vertical tab
            ("\x0cForm", "Form"),    # Form feed
            ("\x0eShift", "Shift"),  # Shift out
            ("\x0fIn", "In"),        # Shift in
            ("\x10Data", "Data"),    # Data link escape
            ("\x11Dev", "Dev"),      # Device control 1
            ("\x12Dev2", "Dev2"),    # Device control 2
            ("\x13Dev3", "Dev3"),    # Device control 3
            ("\x14Dev4", "Dev4"),    # Device control 4
            ("\x15Ack", "Ack"),      # Negative acknowledge
            ("\x16Sync", "Sync"),    # Synchronous idle
            ("\x17End", "End"),      # End of transmission block
            ("\x18Cancel", "Cancel"),# Cancel
            ("\x19EndMed", "EndMed"),# End of medium
            ("\x1aSub", "Sub"),      # Substitute
            ("\x1bEsc", "Esc"),      # Escape
            ("\x1cSep", "Sep"),      # File separator
            ("\x1dSep2", "Sep2"),    # Group separator
            ("\x1eSep3", "Sep3"),    # Record separator
            ("\x1fSep4", "Sep4"),    # Unit separator
            ("\x7fDel", "Del"),      # Delete character
        ]

        for input_str, expected in test_cases:
            result = sanitize_string(input_str)
            assert result == expected, f"Failed for input: {repr(input_str)}, got: {repr(result)}, expected: {repr(expected)}"

    def test_multiple_control_characters(self):
        """Test that multiple control characters in a string are all removed."""
        input_str = "\x00\x01\x02Hello\x03\x04World\x05"
        expected = "HelloWorld"
        result = sanitize_string(input_str)
        assert result == expected

    def test_control_chars_with_latin_text(self):
        """Test control characters mixed with Latin text."""
        input_str = "Hello\x00World\x01Test\x07!"
        expected = "HelloWorldTest!"
        result = sanitize_string(input_str)
        assert result == expected

    def test_private_use_characters(self):
        """Test private use characters (which may not have names)."""
        # Private Use Area characters (U+E000-U+F8FF)
        # These should be filtered out as they're not Latin script
        input_str = "Hello\uE000World\uF8FFTest"
        expected = "HelloWorldTest"
        result = sanitize_string(input_str)
        assert result == expected

    def test_control_characters_not_silently_retained(self):
        """Test that control characters are NOT retained (main issue)."""
        # The issue states that control characters are "silently retained"
        # This test ensures they are actually removed
        control_chars = [
            '\x00', '\x01', '\x02', '\x03', '\x04', '\x05',
            '\x06', '\x07', '\x08', '\x0b', '\x0c', '\x0e',
            '\x0f', '\x10', '\x11', '\x12', '\x13', '\x14',
            '\x15', '\x16', '\x17', '\x18', '\x19', '\x1a',
            '\x1b', '\x1c', '\x1d', '\x1e', '\x1f', '\x7f'
        ]

        for char in control_chars:
            result = sanitize_string(char)
            assert result == "", f"Control character {repr(char)} was not removed, got: {repr(result)}"

    def test_latin_characters_preserved(self):
        """Test that legitimate Latin characters are still preserved."""
        test_cases = [
            ("Hello", "Hello"),
            ("Hello World", "Hello World"),
            ("Café", "Café"),  # Latin with accent
            ("naïve", "naïve"),  # Latin with diaeresis
            ("über", "über"),  # Latin with umlaut
        ]

        for input_str, expected in test_cases:
            result = sanitize_string(input_str)
            assert result == expected, f"Failed for input: {input_str}, got: {result}"

    def test_valueerror_handling_in_is_latin_script(self):
        """Test that ValueError from unicodedata.name() is properly handled."""
        import unicodedata

        # Test that control characters raise ValueError in unicodedata.name()
        control_char = '\x00'
        with pytest.raises(ValueError):
            unicodedata.name(control_char)

        # Test that sanitize_string handles this correctly by removing the character
        result = sanitize_string(control_char)
        assert result == "", "Control character should be removed"

        # Test that normal Latin characters don't raise ValueError
        latin_char = 'A'
        name = unicodedata.name(latin_char)
        assert name.startswith('LATIN')

        # Test that sanitize_string preserves Latin characters
        result = sanitize_string(latin_char)
        assert result == latin_char, "Latin character should be preserved"
