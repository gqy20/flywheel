"""Test to verify Issue #1814 is a false positive.

This test verifies that the JSONFormatter.format method correctly returns
a JSON string value, contradicting the issue report that claims it doesn't.

Issue #1814 claims that the format method is missing a return statement,
but the method actually has a complete implementation with proper return.
"""
import json
import logging
from flywheel.storage import JSONFormatter


class TestIssue1814FalsePositive:
    """Test to verify Issue #1814 is a false positive."""

    def test_format_method_returns_json_string(self):
        """Verify that format() method returns a valid JSON string."""
        formatter = JSONFormatter()

        # Create a basic log record
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message for issue 1814',
            args=(),
            exc_info=None
        )

        # Call format() - should return a JSON string, not None
        result = formatter.format(record)

        # Verify result is not None (the claimed bug)
        assert result is not None, \
            "Issue #1814 FALSE: format() DOES return a value (not None)"

        # Verify result is a string
        assert isinstance(result, str), \
            "Issue #1814 FALSE: format() returns a string"

        # Verify result is valid JSON
        try:
            parsed = json.loads(result)
            assert isinstance(parsed, dict), "Parsed JSON should be a dict"
        except json.JSONDecodeError as e:
            raise AssertionError(
                f"Issue #1814 FALSE: format() returns valid JSON, not: {e}"
            )

        # Verify standard fields are present
        assert 'timestamp' in parsed, "JSON should have timestamp field"
        assert 'level' in parsed, "JSON should have level field"
        assert 'logger' in parsed, "JSON should have logger field"
        assert 'message' in parsed, "JSON should have message field"
        assert parsed['level'] == 'INFO', "Level should be INFO"
        assert parsed['logger'] == 'test_logger', "Logger name should match"
        assert parsed['message'] == 'Test message for issue 1814', "Message should match"

    def test_format_method_with_custom_fields(self):
        """Verify format() returns JSON string with custom extra fields."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name='app.main',
            level=logging.ERROR,
            pathname='app.py',
            lineno=100,
            msg='Error occurred',
            args=(),
            exc_info=None
        )

        # Add custom extra fields
        record.user_id = 12345
        record.request_id = 'abc-123-def'
        record.custom_field = 'custom_value'

        result = formatter.format(record)

        # Verify result exists and is valid JSON
        assert result is not None, "format() should return a value with custom fields"
        assert isinstance(result, str), "format() should return a string"

        parsed = json.loads(result)

        # Verify custom fields are present
        assert 'user_id' in parsed, "Custom field user_id should be in JSON"
        assert 'request_id' in parsed, "Custom field request_id should be in JSON"
        assert 'custom_field' in parsed, "Custom field custom_field should be in JSON"
        assert parsed['user_id'] == 12345
        assert parsed['request_id'] == 'abc-123-def'
        assert parsed['custom_field'] == 'custom_value'

    def test_format_method_with_sensitive_data_redaction(self):
        """Verify format() returns JSON with sensitive fields redacted."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name='auth',
            level=logging.WARNING,
            pathname='auth.py',
            lineno=50,
            msg='Login attempt',
            args=(),
            exc_info=None
        )

        # Add sensitive fields
        record.password = 'secret_password_123'
        record.token = 'secret_token_xyz'
        record.api_key = 'secret_api_key'

        result = formatter.format(record)

        # Verify result exists
        assert result is not None, "format() should return a value even with sensitive data"

        parsed = json.loads(result)

        # Verify sensitive fields are redacted but present
        assert 'password' in parsed, "Password field should be present"
        assert 'token' in parsed, "Token field should be present"
        assert 'api_key' in parsed, "API key field should be present"

        # Verify values are redacted (not the original secrets)
        assert parsed['password'] == '***REDACTED***', "Password should be redacted"
        assert parsed['token'] == '***REDACTED***', "Token should be redacted"
        assert parsed['api_key'] == '***REDACTED***', "API key should be redacted"

    def test_format_method_with_exception(self):
        """Verify format() returns JSON when log record has exception info."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name='test',
            level=logging.ERROR,
            pathname='test.py',
            lineno=1,
            msg='Error with exception',
            args=(),
            exc_info=None
        )

        # Simulate exception info by adding exc_text
        record.exc_info = (Exception, Exception('Test exception'), None)

        result = formatter.format(record)

        # Verify result exists
        assert result is not None, "format() should return a value with exception info"

        parsed = json.loads(result)

        # Verify exception field is present
        assert 'exception' in parsed, "Exception field should be present in JSON"
        assert isinstance(parsed['exception'], str), "Exception should be a string"
        assert len(parsed['exception']) > 0, "Exception should not be empty"

    def test_format_method_completes_full_pipeline(self):
        """Verify format() completes the full formatting pipeline without early return.

        This test specifically addresses the claim in Issue #1814 that the method
        "is interrupted after defining standard_fields" and lacks a return statement.
        """
        formatter = JSONFormatter()

        # Create a record that exercises all code paths:
        # - Standard fields
        # - Custom extra fields
        # - Sensitive data requiring redaction
        # - Large values requiring truncation
        # - Potential JSON serialization issues
        record = logging.LogRecord(
            name='comprehensive_test',
            level=logging.DEBUG,
            pathname='comprehensive.py',
            lineno=999,
            msg='x' * 15000,  # Large message to trigger truncation
            args=(),
            exc_info=None
        )

        # Add various fields
        record.password = 'secret' * 100  # Large sensitive field
        record.user_id = 42
        record.timestamp = '2024-01-01T00:00:00'

        result = formatter.format(record)

        # The method should have completed ALL these steps:
        # 1. Created standard_fields dict
        # 2. Built excluded_fields set
        # 3. Merged custom extra fields
        # 4. Merged context variables
        # 5. Added exception info (if any)
        # 6. Redacted sensitive fields (password)
        # 7. Truncated large values (message)
        # 8. Serialized to JSON
        # 9. Handled JSON size limits
        # 10. RETURNED the result

        assert result is not None, \
            "Issue #1814 FALSE: format() completes full pipeline and returns value"

        # Verify it's valid JSON (proves json.dumps() was called)
        parsed = json.loads(result)

        # Verify redaction happened
        assert parsed['password'] == '***REDACTED***', "Sensitive data should be redacted"

        # Verify truncation happened
        assert len(parsed['message']) < 15000, "Large message should be truncated"

        # All standard fields should be present
        assert 'timestamp' in parsed
        assert 'level' in parsed
        assert 'logger' in parsed
        assert 'message' in parsed
        assert 'thread_id' in parsed
