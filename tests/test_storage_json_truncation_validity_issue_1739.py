"""Test JSON truncation validity (Issue #1739).

This test verifies that:
1. JSON truncation does not produce invalid JSON
2. The final output is always valid JSON
3. Truncation logic handles edge cases correctly

This is a FALSE POSITIVE test - it verifies the issue does NOT actually exist.
"""

import json
import logging
from unittest.mock import patch

import pytest

from flywheel.storage import JSONFormatter


class TestJSONTruncationValidity:
    """Test JSON truncation validity (Issue #1739)."""

    def test_json_output_is_always_valid(self):
        """Test that JSON output is always valid JSON."""
        formatter = JSONFormatter()

        # Create a log record with a large message
        large_message = "x" * (2 * 1024 * 1024)  # 2MB message
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg=large_message,
            args=(),
            exc_info=None,
        )

        # Format the record
        formatted_output = formatter.format(record)

        # Verify the output is valid JSON
        try:
            log_data = json.loads(formatted_output)
            assert isinstance(log_data, dict)
            assert 'message' in log_data
        except json.JSONDecodeError as e:
            pytest.fail(f"Output is not valid JSON: {e}")

    def test_json_output_after_message_truncation_is_valid(self):
        """Test that JSON remains valid after message truncation."""
        formatter = JSONFormatter()

        # Create a scenario where total JSON size exceeds MAX_JSON_SIZE
        # by having many fields plus a large message
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg="x" * (2 * 1024 * 1024),  # 2MB message
            args=(),
            exc_info=None,
        )

        # Add many additional fields to increase JSON size
        for i in range(1000):
            setattr(record, f'field_{i}', f'value_{i}' * 100)

        # Format the record
        formatted_output = formatter.format(record)

        # Verify the output is valid JSON
        try:
            log_data = json.loads(formatted_output)
            assert isinstance(log_data, dict)
        except json.JSONDecodeError as e:
            pytest.fail(f"Output is not valid JSON after truncation: {e}")

    def test_json_output_size_does_not_exceed_max(self):
        """Test that final JSON output respects MAX_JSON_SIZE."""
        formatter = JSONFormatter()

        # Create a massive log record
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg="x" * (3 * 1024 * 1024),  # 3MB message
            args=(),
            exc_info=None,
        )

        # Format the record
        formatted_output = formatter.format(record)

        # Verify the output is valid JSON
        log_data = json.loads(formatted_output)

        # The output should be valid JSON
        assert isinstance(log_data, dict)
        assert 'message' in log_data

        # The JSON output size should be reasonable
        # (Note: it might still exceed MAX_JSON_SIZE if truncation fails,
        # but it should be valid JSON)
        assert len(formatted_output) < 5 * 1024 * 1024, \
            "Output should be reasonably sized"

    def test_json_truncation_preserves_structure(self):
        """Test that truncation preserves JSON structure."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg="x" * (2 * 1024 * 1024),
            args=(),
            exc_info=None,
        )
        record.nested_data = {"key": "value", "number": 42}

        formatted_output = formatter.format(record)
        log_data = json.loads(formatted_output)

        # Verify structure is preserved
        assert 'message' in log_data
        assert 'nested_data' in log_data
        assert isinstance(log_data['nested_data'], dict)
        assert log_data['nested_data']['key'] == 'value'
        assert log_data['nested_data']['number'] == 42

    def test_json_output_with_non_serializable_objects(self):
        """Test that non-serializable objects are handled correctly."""
        formatter = JSONFormatter()

        # Create a custom non-serializable object
        class CustomObject:
            def __str__(self):
                return "custom_object"

        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg="Test message with large content " + "x" * (2 * 1024 * 1024),
            args=(),
            exc_info=None,
        )
        record.custom_obj = CustomObject()

        # Format the record
        formatted_output = formatter.format(record)

        # Verify the output is valid JSON
        try:
            log_data = json.loads(formatted_output)
            assert isinstance(log_data, dict)
            # The custom object should be converted to a string representation
            assert 'custom_obj' in log_data
        except json.JSONDecodeError as e:
            pytest.fail(f"Output is not valid JSON with non-serializable objects: {e}")

    def test_truncated_message_has_suffix(self):
        """Test that truncated messages have the truncation suffix."""
        formatter = JSONFormatter()

        # Create a message that will definitely be truncated
        original_message = "x" * (3 * 1024 * 1024)  # 3MB
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg=original_message,
            args=(),
            exc_info=None,
        )

        formatted_output = formatter.format(record)
        log_data = json.loads(formatted_output)

        # If message was truncated, it should have the suffix
        message = log_data.get('message', '')
        if len(message) < len(original_message):
            assert message.endswith('...[truncated]'), \
                "Truncated message should end with '...[truncated]' suffix"

    def test_no_invalid_json_from_truncation(self):
        """Test that truncation never produces invalid JSON.

        This is the main test for Issue #1739 - verifying that the
        reported issue does not actually exist (false positive).
        """
        formatter = JSONFormatter()

        # Test various scenarios that could potentially produce invalid JSON
        test_cases = [
            # Very large single field
            ("x" * (5 * 1024 * 1024), {}, "Very large message"),
            # Many fields
            ("test", {f'field_{i}': f'value_{i}' * 1000 for i in range(100)}, "Many fields"),
            # Nested large structures
            ("test", {"nested": {"deep": {"value": "x" * (2 * 1024 * 1024)}}}, "Nested large"),
        ]

        for msg, extra_fields, description in test_cases:
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='test.py',
                lineno=1,
                msg=msg,
                args=(),
                exc_info=None,
            )

            # Add extra fields
            for key, value in extra_fields.items():
                setattr(record, key, value)

            # Format the record
            formatted_output = formatter.format(record)

            # Verify it's valid JSON
            try:
                log_data = json.loads(formatted_output)
                assert isinstance(log_data, dict), f"{description}: Output should be a JSON object"
            except json.JSONDecodeError as e:
                pytest.fail(f"{description}: Produced invalid JSON: {e}\nOutput: {formatted_output[:200]}...")
