"""Verification test for Issue #1714 - Methods already exist.

This test verifies that the methods _truncate_large_values and _make_serializable
are properly implemented in the JSONFormatter class.

The issue report was incorrect - these methods already exist and are tested in:
- test_storage_json_log_size_limit_issue_1643.py (tests _truncate_large_values)
- test_issue_1646.py (tests _make_serializable)
"""

import json
import logging
import pytest

from flywheel.storage import JSONFormatter


class TestIssue1714Verification:
    """Verify that the methods mentioned in Issue #1714 exist and work correctly."""

    def test_jsonformatter_has_truncate_large_values_method(self):
        """Test that JSONFormatter has _truncate_large_values method."""
        formatter = JSONFormatter()
        assert hasattr(formatter, '_truncate_large_values'), \
            "JSONFormatter should have _truncate_large_values method"
        assert callable(formatter._truncate_large_values), \
            "_truncate_large_values should be callable"

    def test_jsonformatter_has_make_serializable_method(self):
        """Test that JSONFormatter has _make_serializable method."""
        formatter = JSONFormatter()
        assert hasattr(formatter, '_make_serializable'), \
            "JSONFormatter should have _make_serializable method"
        assert callable(formatter._make_serializable), \
            "_make_serializable should be callable"

    def test_truncate_large_values_works(self):
        """Test that _truncate_large_values method works correctly."""
        formatter = JSONFormatter()

        # Create test data with a large string
        large_string = "x" * 20000  # 20KB
        test_data = {"large_field": large_string, "small_field": "small"}

        # Call the method
        result = formatter._truncate_large_values(test_data)

        # Verify it works
        assert "large_field" in result
        assert "small_field" in result
        assert len(result["large_field"]) <= JSONFormatter.MAX_LOG_SIZE
        assert result["large_field"].endswith("...[truncated]")
        assert result["small_field"] == "small"

    def test_make_serializable_works(self):
        """Test that _make_serializable method works correctly."""
        formatter = JSONFormatter()

        # Create test data with non-serializable object
        class CustomObject:
            def __str__(self):
                return "custom_object"

        test_data = {
            "normal": "value",
            "object": CustomObject(),
            "number": 42
        }

        # Call the method
        result = formatter._make_serializable(test_data)

        # Verify it works - all values should be serializable
        assert "normal" in result
        assert "object" in result
        assert "number" in result
        assert result["normal"] == "value"
        assert result["object"] == "custom_object"
        assert result["number"] == 42

        # Verify the result is JSON-serializable
        json_str = json.dumps(result)
        assert json_str is not None

    def test_format_method_uses_both_methods(self):
        """Test that format method uses both _truncate_large_values and _make_serializable."""
        formatter = JSONFormatter()

        # Create a log record with large string and non-serializable object
        class CustomObject:
            def __str__(self):
                return "custom_object"

        large_string = "x" * 20000
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.large_field = large_string
        record.custom_field = CustomObject()

        # Format the record - this should call both methods internally
        result = formatter.format(record)

        # Verify the result is valid JSON
        assert result is not None
        assert isinstance(result, str)

        # Parse and verify
        parsed = json.loads(result)
        assert "large_field" in parsed
        assert "custom_field" in parsed
        assert len(parsed["large_field"]) <= JSONFormatter.MAX_LOG_SIZE
        assert parsed["custom_field"] == "custom_object"
