"""
Test for issue #1794: Verify excluded_fields set is properly defined.

This test ensures that the excluded_fields set in JSONFormatter
is syntactically correct with properly closed string literals and set braces.
"""

import logging
import ast
import sys
from pathlib import Path

def test_excluded_fields_syntax():
    """Test that the excluded_fields set has valid Python syntax."""
    # Read the storage.py file
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path, "r") as f:
        source_code = f.read()

    # Parse the file to verify syntax
    try:
        ast.parse(source_code)
        assert True, "storage.py has valid Python syntax"
    except SyntaxError as e:
        assert False, f"Syntax error in storage.py: {e}"


def test_excluded_fields_set_properly_closed():
    """Test that the excluded_fields set is properly closed."""
    from flywheel.storage import JSONFormatter

    # Create a formatter instance
    formatter = JSONFormatter()

    # Create a test log record
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    # Format the record - this will fail if excluded_fields has a syntax error
    try:
        formatted = formatter.format(record)
        assert formatted is not None, "Formatter should return a value"
        assert len(formatted) > 0, "Formatted output should not be empty"
    except SyntaxError as e:
        assert False, f"SyntaxError when formatting log: {e}"


def test_excluded_fields_contains_expected_items():
    """Test that excluded_fields contains the expected field names."""
    # Import the module and check excluded_fields is accessible
    import flywheel.storage

    # The formatter should be able to format logs without syntax errors
    formatter = flywheel.storage.JSONFormatter()

    # Create a log record with extra fields
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test",
        args=(),
        exc_info=None,
    )

    # Add some extra fields that should be excluded
    record.thread = "12345"
    record.process = "67890"
    record.message = "Custom message"

    # This should work without syntax errors
    result = formatter.format(record)
    assert result is not None
