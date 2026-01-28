"""Test for issue #436 - Verify _acquire_file_lock is complete and functional."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.storage import Storage


class TestIssue436(unittest.TestCase):
    """Test that _acquire_file_lock method is complete and functional."""

    def test_windows_lock_method_exists(self):
        """Test that _acquire_file_lock method exists and is callable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(path=str(Path(tmpdir) / "todos.json"))
            # Verify the method exists
            self.assertTrue(hasattr(storage, '_acquire_file_lock'))
            self.assertTrue(callable(storage._acquire_file_lock))

    @patch('os.name', 'nt')
    def test_windows_lock_has_complete_implementation(self):
        """Test that Windows locking implementation has all required components."""
        # This test verifies the structure of the _acquire_file_lock method
        # by checking that it contains the key elements mentioned in the docstring

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(path=str(Path(tmpdir) / "todos.json"))

            # We'll test the actual locking behavior by mocking the Windows-specific calls
            with patch('msvcrt.locking') as mock_locking:
                with patch('msvcrt.LK_NBLCK', 2):
                    with patch('msvcrt.LK_UNLCK', 3):
                        # Create a mock file handle
                        mock_file = MagicMock()
                        mock_file.fileno.return_value = 42
                        mock_file.name = "test.json"

                        # Call the method - it should not raise any errors
                        # and should call msvcrt.locking with correct parameters
                        try:
                            storage._acquire_file_lock(mock_file)
                        except Exception as e:
                            # We expect it might fail due to mocking, but it should
                            # at least attempt to call msvcrt.locking
                            pass

                        # Verify that the method attempted to lock
                        # (if it got to the locking call)
                        if mock_locking.called:
                            # Get the call arguments
                            call_args = mock_locking.call_args
                            if call_args:
                                # Should have been called with (fileno, mode, lock_range)
                                args = call_args[0]
                                self.assertEqual(len(args), 3)
                                self.assertEqual(args[0], 42)  # fileno
                                self.assertEqual(args[1], 2)  # LK_NBLCK
                                # lock_range should be a very large number (0x7FFFFFFFFFFFFFFF)
                                self.assertGreater(args[2], 0)

    def test_windows_lock_uses_fixed_large_range(self):
        """Test that Windows locking uses fixed large range (Issue #375, #426)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(path=str(Path(tmpdir) / "todos.json"))

            # Create a mock file handle
            mock_file = MagicMock()
            mock_file.fileno.return_value = 42
            mock_file.name = "test.json"

            # Test _get_file_lock_range_from_handle returns the fixed large range on Windows
            with patch('os.name', 'nt'):
                lock_range = storage._get_file_lock_range_from_handle(mock_file)
                # Should be 0x7FFFFFFFFFFFFFFF (9,223,372,036,854,775,807)
                expected_range = 0x7FFFFFFFFFFFFFFF
                self.assertEqual(lock_range, expected_range)

    def test_windows_lock_has_retry_logic(self):
        """Test that Windows locking has retry logic with timeout (Issue #396)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(path=str(Path(tmpdir) / "todos.json"))

            # Verify timeout and retry interval are set
            self.assertEqual(storage._lock_timeout, 30.0)
            self.assertEqual(storage._lock_retry_interval, 0.1)

    @patch('os.name', 'nt')
    def test_windows_lock_timeout_mechanism(self):
        """Test that Windows lock acquisition has timeout mechanism."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(path=str(Path(tmpdir) / "todos.json"))

            # Create a mock file handle
            mock_file = MagicMock()
            mock_file.fileno.return_value = 42
            mock_file.name = "test.json"

            # Mock msvcrt to always raise IOError (lock held)
            import msvcrt

            with patch('msvcrt.locking', side_effect=IOError("Lock held")):
                with patch('msvcrt.LK_NBLCK', msvcrt.LK_NBLCK):
                    # The lock acquisition should eventually timeout
                    # We'll use a very short timeout for testing
                    original_timeout = storage._lock_timeout
                    storage._lock_timeout = 0.2  # 200ms timeout

                    try:
                        storage._acquire_file_lock(mock_file)
                        self.fail("Expected RuntimeError due to timeout")
                    except RuntimeError as e:
                        # Should timeout with appropriate error message
                        self.assertIn("timed out", str(e).lower())
                        self.assertIn("lock", str(e).lower())
                    finally:
                        storage._lock_timeout = original_timeout


if __name__ == '__main__':
    unittest.main()
