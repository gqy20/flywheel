"""Test for issue #1629: Verify StorageTimeoutError class is complete and properly defined.

This test validates that:
1. The StorageTimeoutError class can be instantiated
2. All __init__ parameters are properly handled
3. The suggested_action attribute works correctly for different operation types
4. The error message formatting works as expected
"""

import pytest
from flywheel.storage import StorageTimeoutError


def test_storage_timeout_error_basic_initialization():
    """Test basic initialization without parameters."""
    error = StorageTimeoutError()
    assert error.timeout is None
    assert error.operation is None
    assert error.caller is None
    assert error.suggested_action == ""
    assert str(error) == ""


def test_storage_timeout_error_with_message():
    """Test initialization with just a message."""
    error = StorageTimeoutError("Operation timed out")
    assert error.timeout is None
    assert error.operation is None
    assert error.caller is None
    assert error.suggested_action == ""
    assert "Operation timed out" in str(error)


def test_storage_timeout_error_with_lock_operation():
    """Test that lock operations get the correct suggested action."""
    error = StorageTimeoutError(
        message="Lock acquisition failed",
        timeout=5.0,
        operation="acquire_lock"
    )
    assert error.timeout == 5.0
    assert error.operation == "acquire_lock"
    assert error.suggested_action == "Retry the operation after a short delay"
    assert "Lock acquisition failed" in str(error)
    assert "timeout=5.0s" in str(error)
    assert "operation=acquire_lock" in str(error)
    assert "suggested_action=Retry the operation after a short delay" in str(error)


def test_storage_timeout_error_with_io_operation():
    """Test that I/O operations get the correct suggested action."""
    error = StorageTimeoutError(
        message="Failed to load cache",
        timeout=10.0,
        operation="load_cache"
    )
    assert error.timeout == 10.0
    assert error.operation == "load_cache"
    assert error.suggested_action == "Check disk space and retry the operation"


def test_storage_timeout_error_with_custom_suggested_action():
    """Test custom suggested action overrides default behavior."""
    error = StorageTimeoutError(
        message="Custom timeout",
        operation="load_cache",
        suggested_action="Try increasing the timeout value"
    )
    assert error.suggested_action == "Try increasing the timeout value"


def test_storage_timeout_error_with_all_parameters():
    """Test initialization with all parameters."""
    error = StorageTimeoutError(
        message="Save operation timed out",
        timeout=15.5,
        operation="save_data",
        caller="Storage.save"
    )
    assert error.timeout == 15.5
    assert error.operation == "save_data"
    assert error.caller == "Storage.save"
    assert error.suggested_action == "Check disk space and retry the operation"

    error_str = str(error)
    assert "Save operation timed out" in error_str
    assert "timeout=15.5s" in error_str
    assert "operation=save_data" in error_str
    assert "caller=Storage.save" in error_str
    assert "suggested_action=Check disk space and retry the operation" in error_str


def test_storage_timeout_error_is_timeout_subclass():
    """Test that StorageTimeoutError is a subclass of TimeoutError."""
    assert issubclass(StorageTimeoutError, TimeoutError)
    error = StorageTimeoutError()
    assert isinstance(error, TimeoutError)


def test_storage_timeout_error_case_insensitive_operation_matching():
    """Test that operation matching is case-insensitive."""
    # Test lock operation with different cases
    error1 = StorageTimeoutError(operation="LOCK")
    assert error1.suggested_action == "Retry the operation after a short delay"

    error2 = StorageTimeoutError(operation="Lock")
    assert error2.suggested_action == "Retry the operation after a short delay"

    # Test I/O operations with different cases
    error3 = StorageTimeoutError(operation="LOAD_DATA")
    assert error3.suggested_action == "Check disk space and retry the operation"

    error4 = StorageTimeoutError(operation="Write")
    assert error4.suggested_action == "Check disk space and retry the operation"


def test_storage_timeout_error_unknown_operation():
    """Test behavior with unknown operation types."""
    error = StorageTimeoutError(operation="unknown_operation")
    assert error.suggested_action == ""


def test_storage_timeout_error_message_formatting():
    """Test that error message formatting handles edge cases."""
    # Test with only message (no context)
    error1 = StorageTimeoutError(message="Simple error")
    assert str(error1) == "Simple error"

    # Test with message and context
    error2 = StorageTimeoutError(
        message="Error with context",
        timeout=5.0,
        operation="test_op"
    )
    error_str = str(error2)
    assert "Error with context" in error_str
    assert "timeout=5.0s" in error_str
    assert "operation=test_op" in error_str

    # Test that parts are joined with " | "
    assert " | " in error_str
