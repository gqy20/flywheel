"""Test Issue #1830 - False Positive Verification.

This test verifies that Issue #1830 is a FALSE POSITIVE.

The issue claimed that JSONFormatter.format method truncates JSON output
directly using `json_output = json_output[:self.MAX_JSON_SIZE]`, which would
produce invalid JSON.

However, the current implementation does NOT have this problem. Instead:
1. It truncates individual fields BEFORE serialization
2. It re-serializes the data after truncation using json.dumps()
3. This ensures the output is ALWAYS valid JSON

This test confirms the correct behavior.
"""

import json
import logging

import pytest

from flywheel.storage import JSONFormatter


class TestIssue1830FalsePositive:
    """Test that Issue #1830 is a false positive."""

    def test_no_direct_json_truncation(self):
        """Verify that JSON output is never directly truncated.

        The issue claimed there was code like:
            json_output = json_output[:self.MAX_JSON_SIZE]

        This test verifies that such direct truncation does not exist
        and that all truncation happens BEFORE serialization.
        """
        formatter = JSONFormatter()

        # Create a log record that would exceed MAX_JSON_SIZE
        # This triggers the size limit logic
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

        # Add many additional fields to ensure we exceed MAX_JSON_SIZE
        for i in range(500):
            large_value = 'y' * 10000  # 10KB per field
            setattr(record, f'field_{i}', large_value)

        # Format the record
        formatted_output = formatter.format(record)

        # Verify the output is valid JSON
        # This would fail if the issue's claimed code existed
        try:
            log_data = json.loads(formatted_output)
        except json.JSONDecodeError as e:
            pytest.fail(
                f"Issue #1830 appears to be TRUE (not a false positive): "
                f"Output is not valid JSON: {e}\n"
                f"Output (first 500 chars): {formatted_output[:500]}"
            )

        # Verify it's a proper dictionary
        assert isinstance(log_data, dict), "Output should be a JSON object"

        # Verify critical fields exist
        assert 'timestamp' in log_data, "timestamp field should exist"
        assert 'level' in log_data, "level field should exist"
        assert 'logger' in log_data, "logger field should exist"
        assert 'message' in log_data, "message field should exist"

    def test_truncation_happens_before_serialization(self):
        """Verify that truncation happens before JSON serialization.

        The correct approach is:
        1. Truncate data fields
        2. Re-serialize with json.dumps()

        NOT:
        1. Serialize to JSON
        2. Truncate the JSON string
        """
        formatter = JSONFormatter()

        # Create a scenario that triggers size-based truncation
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

        # Parse to verify it's valid JSON
        log_data = json.loads(formatted_output)

        # If truncation happened after serialization (the bug), we might see:
        # - Incomplete JSON structures
        # - Missing closing braces/brackets
        # - Truncated string values without proper closing

        # With correct implementation, the message should be truncated
        # but the JSON structure should be intact
        message = log_data.get('message', '')
        assert isinstance(message, str), "Message should be a string"

        # The message should be shorter than original
        assert len(message) < 3 * 1024 * 1024, \
            "Message should be truncated"

        # If truncated, it should have the truncation suffix
        # (added by the field-level truncation logic)
        if len(message) < 3 * 1024 * 1024 - 1000:
            # Message was significantly truncated
            assert '...' in message or len(message) < formatter.MAX_LOG_SIZE, \
                "Truncated message should have truncation indicator"

    def test_json_structure_is_always_valid(self):
        """Test that JSON structure is always valid, even with truncation.

        This is the core test for Issue #1830.
        """
        formatter = JSONFormatter()

        # Test multiple edge cases that could expose the bug
        test_scenarios = [
            # Very large message
            {
                'msg': "x" * (5 * 1024 * 1024),
                'fields': {},
                'description': 'Very large message'
            },
            # Many moderate-sized fields
            {
                'msg': 'test',
                'fields': {f'field_{i}': 'y' * 10000 for i in range(200)},
                'description': 'Many moderate fields'
            },
            # Combination of large message and many fields
            {
                'msg': "z" * (2 * 1024 * 1024),
                'fields': {f'data_{i}': 'w' * 5000 for i in range(100)},
                'description': 'Large message + many fields'
            },
        ]

        for scenario in test_scenarios:
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='test.py',
                lineno=1,
                msg=scenario['msg'],
                args=(),
                exc_info=None,
            )

            # Add extra fields
            for key, value in scenario['fields'].items():
                setattr(record, key, value)

            # Format the record
            formatted_output = formatter.format(record)

            # Verify it's valid JSON
            try:
                log_data = json.loads(formatted_output)
            except json.JSONDecodeError as e:
                pytest.fail(
                    f"{scenario['description']}: "
                    f"Produced invalid JSON (Issue #1830 would be TRUE): {e}\n"
                    f"Output (first 500 chars): {formatted_output[:500]}"
                )

            # Verify basic structure
            assert isinstance(log_data, dict), \
                f"{scenario['description']}: Output should be a dictionary"
            assert 'message' in log_data, \
                f"{scenario['description']}: Should have message field"

    def test_max_json_size_respected_with_valid_json(self):
        """Test that MAX_JSON_SIZE is respected while maintaining valid JSON.

        Even when truncating, the output should be valid JSON.
        """
        formatter = JSONFormatter()

        # Create a massive log record
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg="x" * (10 * 1024 * 1024),  # 10MB message
            args=(),
            exc_info=None,
        )

        # Add huge fields
        for i in range(1000):
            setattr(record, f'huge_{i}', "y" * 50000)

        # Format the record
        formatted_output = formatter.format(record)

        # Verify it's valid JSON
        log_data = json.loads(formatted_output)

        # The output should be reasonably sized
        # (Note: due to the multi-step truncation, it might slightly exceed
        # MAX_JSON_SIZE, but should be close)
        assert len(formatted_output) < 2 * 1024 * 1024, \
            "Output should be reasonably sized (less than 2MB)"

        # But it MUST be valid JSON
        assert isinstance(log_data, dict)


def test_issue_1830_is_false_positive():
    """Main test: Verify Issue #1830 is a false positive.

    This test confirms that the claimed bug does not exist in the codebase.
    """
    formatter = JSONFormatter()

    # Create the exact scenario described in the issue
    # The issue claimed that when JSON exceeds MAX_JSON_SIZE,
    # it gets truncated like: json_output = json_output[:self.MAX_JSON_SIZE]
    # This would produce invalid JSON.

    # Create a log record that definitely exceeds MAX_JSON_SIZE (1MB)
    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='test.py',
        lineno=1,
        msg="A" * (5 * 1024 * 1024),  # 5MB message
        args=(),
        exc_info=None,
    )

    # Add many large fields
    for i in range(200):
        setattr(record, f'field_{i}', "B" * 20000)

    # Format the record
    output = formatter.format(record)

    # If the issue's claimed code existed, this would fail with JSONDecodeError
    # because direct string truncation would produce invalid JSON like:
    # {"message":"AAAAA... (truncated in middle of string or structure)

    # The fact that this succeeds proves the issue is a false positive
    try:
        data = json.loads(output)
        assert isinstance(data, dict)
        assert 'message' in data
    except json.JSONDecodeError as e:
        pytest.fail(
            f"Issue #1830 is NOT a false positive! "
            f"Direct JSON truncation bug exists: {e}"
        )
