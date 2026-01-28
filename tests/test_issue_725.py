"""Test cases for Issue #725 - Hyphen removal causes legitimate content corruption.

Issue #725 reports that sanitize_string removes hyphens, which can cause
data corruption for:
- UUIDs (e.g., "550e8400-e29b-41d4-a716-446655440000")
- Words with hyphens (e.g., "well-known", "self-contained", "multi-step")
- Date strings (e.g., "2024-01-15")
- Phone numbers (e.g., "1-800-555-0123")

The issue suggests evaluating whether hyphens must be removed. If context allows
(such as when not used in command-line arguments), hyphens should be preserved,
or only removed in specific contexts.

These tests verify that hyphens are preserved to prevent data corruption while
maintaining security.
"""

import pytest
from flywheel.cli import sanitize_string


class TestSanitizeStringIssue725:
    """Tests for verify that sanitize_string preserves hyphens.

    Hyphens are legitimate characters in many contexts:
    - UUIDs (550e8400-e29b-41d4-a716-446655440000)
    - Hyphenated words (well-known, self-contained, multi-step)
    - ISO dates (2024-01-15)
    - Phone numbers (1-800-555-0123)
    - URLs and paths

    Issue #725: Removing hyphens causes data corruption and should be avoided
    when storage backends support parameterized queries.
    """

    def test_preserves_uuid_with_hyphens(self):
        """Test that UUIDs with hyphens are preserved."""
        # Standard UUID format
        input_str = "550e8400-e29b-41d4-a716-446655440000"
        result = sanitize_string(input_str)
        assert '-' in result, "Hyphens in UUIDs should be preserved"
        assert result == "550e8400-e29b-41d4-a716-446655440000", \
            "UUIDs should remain intact"

    def test_preserves_hyphenated_words(self):
        """Test that hyphenated compound words are preserved."""
        # Common hyphenated words
        test_cases = [
            "well-known",
            "self-contained",
            "multi-step",
            "state-of-the-art",
            "mother-in-law",
            "twenty-one",
        ]
        for word in test_cases:
            result = sanitize_string(word)
            assert '-' in result, f"Hyphens in '{word}' should be preserved"
            assert result == word, f"Hyphenated word '{word}' should remain intact"

    def test_preserves_iso_date_strings(self):
        """Test that ISO date strings with hyphens are preserved."""
        # ISO 8601 date format
        input_str = "2024-01-15"
        result = sanitize_string(input_str)
        assert '-' in result, "Hyphens in ISO dates should be preserved"
        assert result == "2024-01-15", "ISO dates should remain intact"

    def test_preserves_iso_datetime_strings(self):
        """Test that ISO datetime strings with hyphens are preserved."""
        # ISO 8601 datetime format
        input_str = "2024-01-15T10:30:00"
        result = sanitize_string(input_str)
        assert '-' in result, "Hyphens in ISO datetimes should be preserved"
        assert result == "2024-01-15T10:30:00", "ISO datetimes should remain intact"

    def test_preserves_phone_numbers_with_hyphens(self):
        """Test that phone numbers with hyphens are preserved."""
        # Common phone number format
        input_str = "1-800-555-0123"
        result = sanitize_string(input_str)
        assert '-' in result, "Hyphens in phone numbers should be preserved"
        assert result == "1-800-555-0123", "Phone numbers should remain intact"

    def test_preserves_urls_with_hyphens(self):
        """Test that URLs with hyphens are preserved."""
        # URLs often contain hyphens
        input_str = "https://example.com/my-page-name"
        result = sanitize_string(input_str)
        assert '-' in result, "Hyphens in URLs should be preserved"
        assert result == "https://example.com/my-page-name", "URLs should remain intact"

    def test_preserves_file_paths_with_hyphens(self):
        """Test that file paths with hyphens are preserved."""
        # File and directory names often contain hyphens
        input_str = "/home/user/my-project/file-name.txt"
        result = sanitize_string(input_str)
        assert '-' in result, "Hyphens in file paths should be preserved"
        assert result == "/home/user/my-project/file-name.txt", \
            "File paths should remain intact"

    def test_preserves_text_with_multiple_hyphens(self):
        """Test that text with multiple hyphens is preserved."""
        # Text containing multiple hyphenated words
        input_str = "This is a well-known, self-contained example"
        result = sanitize_string(input_str)
        assert '-' in result, "Multiple hyphens should be preserved"
        assert result == "This is a well-known, self-contained example", \
            "Text with hyphens should remain intact"

    def test_preserves_serial_numbers_with_hyphens(self):
        """Test that serial numbers with hyphens are preserved."""
        # Serial numbers often use hyphens
        input_str = "SN-12345-ABC-67890"
        result = sanitize_string(input_str)
        assert '-' in result, "Hyphens in serial numbers should be preserved"
        assert result == "SN-12345-ABC-67890", "Serial numbers should remain intact"

    def test_still_removes_dangerous_shell_operators(self):
        """Test that dangerous shell operators are still removed."""
        # Shell injection metacharacters should still be removed
        input_str = "Test; echo hacked | cat"
        result = sanitize_string(input_str)
        assert ';' not in result, "Shell operators should be removed"
        assert '|' not in result, "Pipe operators should be removed"
        assert 'echo' in result, "Legitimate text should be preserved"

    def test_still_removes_curly_braces_for_format_string_protection(self):
        """Test that curly braces are still removed to prevent format string attacks."""
        # Curly braces should still be removed as per Issue #690
        input_str = "Test {variable} String"
        result = sanitize_string(input_str)
        assert '{' not in result, "Opening curly brace should be removed"
        assert '}' not in result, "Closing curly brace should be removed"

    def test_hyphen_at_end_of_sentence_preserved(self):
        """Test that hyphens at the end of text are preserved."""
        input_str = "This is my-text-"
        result = sanitize_string(input_str)
        assert result == "This is my-text-", "Trailing hyphens should be preserved"

    def test_hyphen_at_start_of_text_preserved(self):
        """Test that hyphens at the start of text are preserved."""
        input_str = "-prefix-option"
        result = sanitize_string(input_str)
        assert result == "-prefix-option", "Leading hyphens should be preserved"
