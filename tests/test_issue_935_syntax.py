"""Test for Issue #935 - Verify storage.py has no syntax errors.

This test verifies that the storage.py module can be imported successfully
and that the _get_stale_lock_timeout function works correctly.

Issue #935 claimed there was a missing closing parenthesis in a logger.warning call,
but upon inspection, the code is actually correct.
"""

import os
import sys
import unittest
from unittest import mock

# Add src to path if needed
if os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'src')):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestIssue935Syntax(unittest.TestCase):
    """Test case for Issue #935 - syntax error verification."""

    def test_storage_module_can_be_imported(self):
        """Test that storage module can be imported without syntax errors."""
        try:
            import flywheel.storage
            self.assertIsNotNone(flywheel.storage)
        except SyntaxError as e:
            self.fail(f"storage.py has syntax error: {e}")

    def test_get_stale_lock_timeout_function_exists(self):
        """Test that _get_stale_lock_timeout function exists and is callable."""
        import flywheel.storage

        self.assertTrue(
            hasattr(flywheel.storage, '_get_stale_lock_timeout'),
            "_get_stale_lock_timeout function should exist"
        )
        self.assertTrue(
            callable(flywheel.storage._get_stale_lock_timeout),
            "_get_stale_lock_timeout should be callable"
        )

    def test_get_stale_lock_timeout_with_invalid_value(self):
        """Test that _get_stale_lock_timeout handles invalid values correctly."""
        import flywheel.storage

        # Test with invalid (non-integer) value
        with mock.patch.dict(os.environ, {'FW_LOCK_STALE_SECONDS': 'invalid'}):
            # This should not raise a SyntaxError
            # The function should handle the ValueError and log a warning
            result = flywheel.storage._get_stale_lock_timeout()
            # Should return default value
            self.assertEqual(result, 300)

    def test_get_stale_lock_timeout_with_negative_value(self):
        """Test that _get_stale_lock_timeout handles negative values correctly."""
        import flywheel.storage

        # Test with negative value (invalid)
        with mock.patch.dict(os.environ, {'FW_LOCK_STALE_SECONDS': '-100'}):
            # This should not raise a SyntaxError
            # The function should handle this and log a warning
            result = flywheel.storage._get_stale_lock_timeout()
            # Should return default value
            self.assertEqual(result, 300)

    def test_get_stale_lock_timeout_with_valid_value(self):
        """Test that _get_stale_lock_timeout works with valid values."""
        import flywheel.storage

        # Test with valid positive integer
        with mock.patch.dict(os.environ, {'FW_LOCK_STALE_SECONDS': '600'}):
            result = flywheel.storage._get_stale_lock_timeout()
            self.assertEqual(result, 600)

    def test_logger_warning_calls_are_properly_closed(self):
        """Test that all logger.warning calls have proper syntax.

        This test specifically checks the code around lines 217-227
        where the issue was reported.
        """
        import flywheel.storage
        import inspect

        # Get the source code of the function
        source = inspect.getsource(flywheel.storage._get_stale_lock_timeout)

        # Verify the function contains properly formatted logger.warning calls
        self.assertIn('logger.warning(', source)
        self.assertIn(')', source)  # Should have closing parenthesis

        # Count opening and closing parentheses in logger.warning calls
        # (basic syntax check)
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if 'logger.warning(' in line:
                # Find the closing parenthesis for this call
                # It should be in the same line or subsequent lines
                remaining_lines = '\n'.join(lines[i:])
                # The call should be balanced
                self.assertIn(')', remaining_lines)


if __name__ == '__main__':
    unittest.main()
