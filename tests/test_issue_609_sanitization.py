"""Tests for issue #609 - sanitization of title and description fields.

This test suite ensures that title and description fields are properly sanitized
to prevent injection attacks when data is rendered or executed by storage backends.
"""

import pytest

from flywheel.cli import sanitize_string


class TestSanitizeString:
    """Test suite for the sanitize_string function."""

    def test_sanitizes_html_tags(self):
        """Test that HTML tags are removed from strings."""
        assert sanitize_string("<script>alert('xss')</script>") == "scriptalert('xss')/script"
        assert sanitize_string("<b>bold</b>") == "bbold/b"
        assert sanitize_string("Hello <img src=x onerror=alert(1)>") == "Hello img src=x onerror=alert(1)"

    def test_sanitizes_shell_metacharacters(self):
        """Test that shell metacharacters are removed."""
        assert sanitize_string("title; rm -rf /") == "title rm -rf /"
        assert sanitize_string("title | cat /etc/passwd") == "title  cat /etc/passwd"
        assert sanitize_string("title && evil") == "title  evil"
        assert sanitize_string("title `whoami`") == "title whoami"
        assert sanitize_string("title $(evil)") == "title evil"

    def test_sanitizes_control_characters(self):
        """Test that control characters are removed."""
        assert sanitize_string("title\x00null") == "titlenull"
        assert sanitize_string("title\nnewline") == "titlenewline"
        assert sanitize_string("title\ttab") == "titletab"
        assert sanitize_string("title\rcarriage") == "titlecarriage"

    def test_sanitizes_unicode_spoofing_characters(self):
        """Test that Unicode spoofing characters are removed."""
        # Fullwidth characters
        assert sanitize_string("ＦＵＬＬＷＩＤＴＨ") == ""
        # Zero-width characters
        assert sanitize_string("title\u200Bzero") == "titlezero"
        # Bidirectional override
        assert sanitize_string("title\u202Eattack") == "titleattack"

    def test_preserves_safe_characters(self):
        """Test that safe characters are preserved."""
        assert sanitize_string("Normal Title 123") == "Normal Title 123"
        assert sanitize_string("Hello-World_Test") == "Hello-World_Test"
        assert sanitize_string("user@example.com") == "userexample.com"
        assert sanitize_string("price: $100") == "price: 100"

    def test_handles_empty_string(self):
        """Test that empty strings are handled correctly."""
        assert sanitize_string("") == ""

    def test_handles_whitespace(self):
        """Test that whitespace is preserved appropriately."""
        assert sanitize_string("  spaced  out  ") == "  spaced  out  "
        assert sanitize_string("multi\nline") == "multiline"

    def test_removes_quotes_for_json_safety(self):
        """Test that quotes are removed for JSON safety."""
        assert sanitize_string('title with "quotes"') == "title with quotes"
        assert sanitize_string("title with 'apostrophes'") == "title with apostrophes"
        assert sanitize_string('title with `backticks`') == "title with backticks"

    def test_description_sanitization(self):
        """Test that description field is also sanitized."""
        long_desc = """This is a description with <script>evil()</script>
        and shell commands: ; rm -rf /
        and quotes: "double" 'single' `backtick`"""
        result = sanitize_string(long_desc)
        assert "<script>" not in result
        assert ";" not in result
        assert '"' not in result
        assert "'" not in result
        assert "`" not in result
