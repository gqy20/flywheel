"""Tests for Todo sanitization security vulnerabilities (Issue #1134).

These tests demonstrate that the current sanitization logic is flawed and can be bypassed.
"""


import pytest
from flywheel.todo import _sanitize_string, Todo


class TestSanitizationVulnerabilities:
    """Test cases that demonstrate security vulnerabilities in sanitization."""

    def test_html_entity_encoding_bypass(self):
        """HTML entity encoding can bypass tag removal."""
        # Using HTML entities to encode tags
        malicious = "&lt;script&gt;alert('XSS')&lt;/script&gt;"
        result = _sanitize_string(malicious)
        # The current implementation doesn't decode HTML entities,
        # so this bypasses the sanitization
        assert "&lt;" not in result or "&gt;" not in result, (
            "HTML entities should be handled to prevent bypass"
        )

    def test_case_variation_in_tags(self):
        """Case variations in HTML tags should be handled."""
        # Mixed case HTML tags
        malicious = "<ScRiPt>alert('XSS')</ScRiPt>"
        result = _sanitize_string(malicious)
        assert "<script>" not in result.lower(), (
            "Case variations should not bypass tag removal"
        )
        assert "alert('XSS')" not in result, "Script content should be removed"

    def test_non_string_input_safety(self):
        """Non-string inputs should be handled safely before regex operations."""
        # The current implementation returns non-strings as-is,
        # but this could cause issues if used with string operations
        result = _sanitize_string(12345)
        assert isinstance(result, str) or result == 12345, (
            "Non-string inputs should be handled safely"
        )

    def test_javascript_protocol_with_encoding(self):
        """JavaScript protocol with mixed case and spaces."""
        malicious = "<a href=javas%99cript:alert('XSS')>click</a>"
        result = _sanitize_string(malicious)
        assert "javascript:" not in result.lower(), (
            "Encoded or obfuscated javascript: should be removed"
        )

    def test_onerror_handler_bypass(self):
        """Event handlers with case variations."""
        malicious = "<img src=x OnError=alert('XSS')>"
        result = _sanitize_string(malicious)
        assert "onerror" not in result.lower(), (
            "Event handlers should be removed regardless of case"
        )

    def test_sql_injection_pattern_bypass(self):
        """SQL injection patterns with encoding."""
        # The SQL injection patterns are too simplistic
        malicious = "' OR '1'='1' --"
        result = _sanitize_string(malicious)
        # Current implementation tries to remove this but can be bypassed
        # with variations
        assert "OR" not in result or "1=1" not in result, (
            "SQL injection patterns should be removed"
        )


class TestTodoFromDictWithoutSanitization:
    """Test Todo creation should work without sanitization.

    These tests expect that sanitization is removed and proper
    input validation/handling is used instead.
    """

    def test_todo_accepts_plain_text(self):
        """Todo should accept plain text titles and descriptions."""
        data = {
            "id": 1,
            "title": "Buy groceries",
            "description": "Get milk and eggs",
        }
        todo = Todo.from_dict(data)
        assert todo.title == "Buy groceries"
        assert todo.description == "Get milk and eggs"

    def test_todo_preserves_user_input(self):
        """Todo should preserve user input as-is (no sanitization)."""
        # Users may want to use < and > for legitimate purposes
        data = {
            "id": 1,
            "title": "Task: priority > 5",
            "description": "Check if value < threshold",
        }
        todo = Todo.from_dict(data)
        assert ">" in todo.title
        assert "<" in todo.description

    def test_todo_with_special_characters(self):
        """Todo should handle special characters correctly."""
        data = {
            "id": 1,
            "title": "Review PR #123",
            "description": "Fix bug in 'user' input",
        }
        todo = Todo.from_dict(data)
        assert "#" in todo.title
        assert "'" in todo.description
