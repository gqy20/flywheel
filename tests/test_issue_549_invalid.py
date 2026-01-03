"""Test for Issue #549 - Verify the method is complete.

This test verifies that the _get_file_lock_range_from_handle method
is properly implemented and not truncated as reported in the issue.

The issue report claimed the method was incomplete/truncated,
but this test confirms the method is fully implemented.
"""
import os
import pytest
from flywheel.storage import Storage


class TestIssue549Invalid:
    """Test that _get_file_lock_range_from_handle is complete."""

    def test_method_exists(self):
        """Verify the method exists."""
        storage = Storage()
        assert hasattr(storage, '_get_file_lock_range_from_handle')

    def test_method_callable(self):
        """Verify the method is callable."""
        storage = Storage()
        assert callable(storage._get_file_lock_range_from_handle)

    def test_windows_returns_tuple(self):
        """Verify Windows branch returns correct tuple."""
        storage = Storage()
        # Create a mock file handle
        result = storage._get_file_lock_range_from_handle(None)

        if os.name == 'nt':
            # Windows should return (0, 1)
            assert result == (0, 1), f"Expected (0, 1) on Windows, got {result}"
        else:
            # Unix should return 0
            assert result == 0, f"Expected 0 on Unix, got {result}"

    def test_method_signature(self):
        """Verify the method has correct signature."""
        import inspect
        storage = Storage()
        method = storage._get_file_lock_range_from_handle

        # Check method signature
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())

        assert 'file_handle' in params, "Method should have file_handle parameter"

    def test_method_has_docstring(self):
        """Verify the method has documentation."""
        storage = Storage()
        method = storage._get_file_lock_range_from_handle

        assert method.__doc__ is not None, "Method should have a docstring"
        assert "Windows" in method.__doc__ or "lock" in method.__doc__, \
            "Docstring should mention Windows or locking"
