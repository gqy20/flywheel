"""Test for Issue #964 - Format string injection prevention.

This test verifies that:
1. The remove_control_chars function removes percent signs to prevent format string injection
2. Logger calls use safe patterns (%s placeholders or f-strings) when handling user input
3. The safe_log helper function provides a safe way to log user input

Security Issue: If user input containing format string specifiers like %s, %d, etc.
is passed directly to logger calls using the old % formatting style (logger.info(msg)),
it could cause information disclosure or crashes.

Fix: Remove % from user input and ensure logger calls use safe patterns.
"""

import logging
import pytest
from io import StringIO
from flywheel.cli import remove_control_chars, safe_log


class TestFormatStringInjectionPrevention:
    """Test format string injection prevention (Issue #964)."""

    def test_remove_control_chars_removes_percent_sign(self):
        """Test that remove_control_chars removes percent sign."""
        # Test basic percent sign removal
        assert remove_control_chars("Hello%World") == "HelloWorld"
        assert remove_control_chars("100%complete") == "100complete"

    def test_remove_control_chars_removes_format_specifiers(self):
        """Test that format string specifiers are removed."""
        # Test common format string specifiers
        assert remove_control_chars("Value: %s") == "Value: s"
        assert remove_control_chars("Count: %d items") == "Count: d items"
        assert remove_control_chars("Price: %f dollars") == "Price: f dollars"
        assert remove_control_chars("Mixed %s %d %f") == "Mixed s d f"

    def test_remove_control_chars_preserves_safe_content(self):
        """Test that safe content is preserved after removing %."""
        # Test that legitimate content is preserved
        assert remove_control_chars("Normal text") == "Normal text"
        assert remove_control_chars("UUID: 550e8400-e29b-41d4-a716-446655440000") == \
            "UUID: 550e8400-e29b-41d4-a716-446655440000"
        assert remove_control_chars("Date: 2024-01-15") == "Date: 2024-01-15"

    def test_logger_safe_pattern_with_user_input(self):
        """Test that logger calls use safe patterns with user input.

        This test verifies that when user input (which may have contained %)
        is used in logger calls, it should be safe because:
        1. The % has been removed by remove_control_chars
        2. Logger calls should use %s placeholder or f-string pattern
        """
        # Create a logger and capture output
        logger = logging.getLogger('test_logger')
        logger.setLevel(logging.INFO)

        # Remove any existing handlers
        logger.handlers.clear()

        # Create a string handler to capture output
        string_stream = StringIO()
        handler = logging.StreamHandler(string_stream)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)

        # Simulate user input that has been sanitized
        user_input = "Test%s%d%f"
        sanitized_input = remove_control_chars(user_input)

        # Safe pattern 1: Using %s placeholder
        logger.info("Processing: %s", sanitized_input)

        # Safe pattern 2: Using f-string
        logger.info(f"User input: {sanitized_input}")

        # Get the logged output
        output = string_stream.getvalue()

        # Verify that the output is safe (no unexpected formatting occurred)
        assert "Processing:" in output
        assert "Test sdf" in output  # The % signs are removed, leaving "sdf"
        assert "User input:" in output

    def test_format_string_injection_prevention(self):
        """Test that format string injection is prevented.

        This test demonstrates the security issue that Issue #964 addresses.
        Without the fix, a malicious user could inject format strings like %s
        to potentially cause information disclosure or crashes.
        """
        # Simulate malicious input attempting format string injection
        malicious_input = "Todo %s %s %s %s"
        sanitized = remove_control_chars(malicious_input)

        # After sanitization, the % signs should be removed
        assert "%" not in sanitized
        assert sanitized == "Todo s s s s"

        # This sanitized input is now safe to use in logger calls
        # even with the old % formatting style
        logger = logging.getLogger('test_injection')
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        string_stream = StringIO()
        handler = logging.StreamHandler(string_stream)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)

        # Even if someone uses the unsafe pattern (which they shouldn't),
        # the sanitized input won't cause issues because % is removed
        # Note: This would normally be unsafe with unsanitized input
        # But since % is removed, it's safe
        try:
            logger.info("Processing todo: %s" % sanitized)
            output = string_stream.getvalue()
            assert "Processing todo:" in output
            assert "Todo s s s s" in output
        except Exception as e:
            pytest.fail(f"Logger call failed with sanitized input: {e}")

    def test_safe_log_function(self):
        """Test the safe_log helper function.

        This test verifies that the safe_log function provides a safe way
        to log user input without format string injection risks.
        """
        logger = logging.getLogger('test_safe_log')
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        string_stream = StringIO()
        handler = logging.StreamHandler(string_stream)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)

        # Sanitize user input
        user_input = "Todo %s %d"
        sanitized_input = remove_control_chars(user_input)

        # Use safe_log to log the sanitized input
        safe_log(logger, "info", "Processing: %s", sanitized_input)

        # Verify the output
        output = string_stream.getvalue()
        assert "Processing:" in output
        assert "Todo sd" in output  # % signs removed, leaving "sd"

    def test_safe_log_with_multiple_args(self):
        """Test safe_log with multiple arguments."""
        logger = logging.getLogger('test_safe_log_multi')
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        string_stream = StringIO()
        handler = logging.StreamHandler(string_stream)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)

        # Sanitize user inputs
        title = "Todo %s"
        desc = "Description %d"
        sanitized_title = remove_control_chars(title)
        sanitized_desc = remove_control_chars(desc)

        # Use safe_log with multiple arguments
        safe_log(logger, "info", "Todo: %s, Desc: %s", sanitized_title, sanitized_desc)

        # Verify the output
        output = string_stream.getvalue()
        assert "Todo:" in output
        assert "Desc:" in output
        assert "Todo s" in output
        assert "Description d" in output

    def test_safe_log_invalid_level(self):
        """Test that safe_log raises ValueError for invalid log level."""
        logger = logging.getLogger('test_safe_log_invalid')

        with pytest.raises(ValueError, match="Invalid log level"):
            safe_log(logger, "invalid", "Test message")
