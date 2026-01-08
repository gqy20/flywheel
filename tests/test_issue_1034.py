"""Tests for Issue #1034 - Format string characters should be preserved in general context.

Issue #1034 reports that remove_control_chars() removes format string characters
({, }, %) in general context, which can corrupt legitimate user content like:
- Code snippets: "Use {key: value} in Python"
- Math expressions: "Complete 50% of the task"
- JSON data: '{"name": "test"}'
- Template literals: "Replace {variable} with value"

The function should preserve these characters in general context and only remove
them when explicitly requested for security-sensitive contexts.
"""

import pytest

from flywheel.cli import remove_control_chars


class TestFormatStringPreservation:
    """Test that format string characters are preserved in general context.

    This addresses Issue #1034 which identified that removing format string
    characters ({, }, %) in general context corrupts legitimate user content.
    """

    def test_curly_braces_preserved_in_code_snippets(self):
        """Curly braces in code snippets should be preserved."""
        # Python dict example
        input_str = "Use {'key': 'value'} for dictionaries"
        result = remove_control_chars(input_str)
        assert result == input_str, f"Expected '{input_str}', got '{result}'"

    def test_curly_braces_preserved_in_json(self):
        """Curly braces in JSON examples should be preserved."""
        # JSON example
        input_str = 'Format: {"name": "test", "count": 5}'
        result = remove_control_chars(input_str)
        assert result == input_str, f"Expected '{input_str}', got '{result}'"

    def test_curly_braces_preserved_in_placeholders(self):
        """Curly braces used as placeholders should be preserved."""
        # Template placeholder example
        input_str = "Replace {username} with actual name"
        result = remove_control_chars(input_str)
        assert result == input_str, f"Expected '{input_str}', got '{result}'"

    def test_percent_sign_preserved_in_percentages(self):
        """Percent signs in percentage values should be preserved."""
        # Percentage example
        input_str = "Complete 50% of the task"
        result = remove_control_chars(input_str)
        assert result == input_str, f"Expected '{input_str}', got '{result}'"

    def test_percent_sign_preserved_in_discounts(self):
        """Percent signs in discount information should be preserved."""
        # Discount example
        input_str = "Get 20% off on all items"
        result = remove_control_chars(input_str)
        assert result == input_str, f"Expected '{input_str}', got '{result}'"

    def test_percent_sign_preserved_in_progress(self):
        """Percent signs in progress indicators should be preserved."""
        # Progress example
        input_str = "Progress: 75% completed"
        result = remove_control_chars(input_str)
        assert result == input_str, f"Expected '{input_str}', got '{result}'"

    def test_combined_format_characters_preserved(self):
        """Multiple format characters in the same string should all be preserved."""
        # Complex example with both {} and %
        input_str = "Process {items} with 100% efficiency"
        result = remove_control_chars(input_str)
        assert result == input_str, f"Expected '{input_str}', got '{result}'"

    def test_nested_curly_braces_preserved(self):
        """Nested curly braces should be preserved."""
        # Nested braces example
        input_str = "Use format {outer: {inner: value}}"
        result = remove_control_chars(input_str)
        assert result == input_str, f"Expected '{input_str}', got '{result}'"

    def test_backslash_preserved_in_paths(self):
        """Backslashes in file paths should be preserved."""
        # Windows path example (though note this is for data storage, not shell context)
        input_str = "Path: C:\\Users\\Documents\\file.txt"
        result = remove_control_chars(input_str)
        # Note: Current implementation removes backslashes, but this test
        # documents the expected behavior for Issue #1034
        # This test will fail until we implement the fix
        assert result == input_str, f"Expected '{input_str}', got '{result}'"
