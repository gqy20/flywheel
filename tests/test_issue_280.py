"""Test TOCTOU fix in Windows lock range calculation (Issue #280).

This test verifies that the Time-Of-Check to Time-Of-Use (TOCTOU) race condition
in _get_windows_lock_range has been fixed.

The vulnerability: The old code checked if a file exists before getting its size,
creating a time window where the file could be deleted or truncated, causing
incorrect lock ranges or lock failures.

The fix: Use a large fixed lock range (0xFFFF0000) instead of checking file
existence and getting its size. This eliminates the TOCTOU vulnerability entirely.
"""

import os
import tempfile
from pathlib import Path
import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestIssue280TOCTOUFix:
    """Test that TOCTOU vulnerability in Windows lock range is fixed."""

    def test_no_toctou_in_windows_lock_range(self):
        """Test that _get_windows_lock_range doesn't have TOCTOU vulnerability.

        The old vulnerable code was:
            if file_path.exists():
                return os.path.getsize(file_path)

        This has a TOCTOU race condition between exists() and getsize().

        The fix: Return a large fixed value without checking file state.
        This eliminates the race condition entirely.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_toctou.json"
            storage = Storage(str(storage_path))

            # Get lock range - should not raise any exceptions
            # and should not depend on file existence
            lock_range = storage._get_windows_lock_range(storage_path)

            # Verify it returns a valid large fixed value
            assert isinstance(lock_range, int)
            assert lock_range > 0

            # On Windows, verify it uses the large fixed range (0xFFFF0000)
            # instead of checking file existence and size
            if os.name == 'nt':
                assert lock_range == 0xFFFF0000, (
                    f"Expected fixed lock range 0xFFFF0000, got {lock_range}. "
                    "The TOCTOU vulnerability fix should use a fixed value."
                )

    def test_lock_range_independent_of_file_state(self):
        """Test that lock range doesn't change based on file state.

        This ensures no TOCTOU vulnerability: the lock range should be the
        same whether the file exists, doesn't exist, is empty, or is large.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_independent.json"
            storage = Storage(str(storage_path))

            # Get lock range when file doesn't exist
            nonexistent_path = Path(tmpdir) / "nonexistent.json"
            lock_range1 = storage._get_windows_lock_range(nonexistent_path)

            # Add todos to create a file
            storage.add(Todo(title="Task 1"))
            storage.add(Todo(title="Task 2"))

            # Get lock range when file exists and is small
            lock_range2 = storage._get_windows_lock_range(storage_path)

            # Add many todos to make file larger
            for i in range(100):
                storage.add(Todo(title=f"Large task {i}" * 10))

            # Get lock range when file exists and is large
            lock_range3 = storage._get_windows_lock_range(storage_path)

            # All lock ranges should be identical (no TOCTOU)
            assert lock_range1 == lock_range2 == lock_range3, (
                f"Lock range should be independent of file state to avoid TOCTOU. "
                f"Got ranges: nonexistent={lock_range1}, small={lock_range2}, large={lock_range3}"
            )

            # On Windows, should be the fixed value
            if os.name == 'nt':
                assert lock_range1 == 0xFFFF0000

    def test_lock_range_no_filesystem_access(self):
        """Test that lock range doesn't access filesystem.

        The old vulnerable code accessed filesystem (exists() and getsize()),
        creating TOCTOU vulnerability. The fix should avoid filesystem access.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_no_access.json"
            storage = Storage(str(storage_path))

            # Even for a path that doesn't exist and can't be accessed,
            # _get_windows_lock_range should work without touching filesystem
            impossible_path = Path("/nonexistent/deeply/nested/path/that/does/not/exist.json")

            # Should not raise FileNotFoundError, OSError, or any other exception
            lock_range = storage._get_windows_lock_range(impossible_path)

            # Should still return a valid value
            assert isinstance(lock_range, int)
            assert lock_range > 0

            # On Windows, should be the fixed value
            if os.name == 'nt':
                assert lock_range == 0xFFFF0000

    def test_lock_range_thread_safety(self):
        """Test that lock range calculation is thread-safe.

        Since _get_windows_lock_range doesn't access filesystem (no TOCTOU),
        it should be safe to call from multiple threads without race conditions.
        """
        import threading

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_thread_safety.json"
            storage = Storage(str(storage_path))

            results = []
            errors = []

            def get_lock_range():
                try:
                    lock_range = storage._get_windows_lock_range(storage_path)
                    results.append(lock_range)
                except Exception as e:
                    errors.append(e)

            # Create multiple threads that all call _get_windows_lock_range
            threads = []
            for _ in range(10):
                t = threading.Thread(target=get_lock_range)
                threads.append(t)
                t.start()

            # Wait for all threads to complete
            for t in threads:
                t.join()

            # No errors should have occurred
            assert len(errors) == 0, (
                f"Thread-safe lock range calculation raised errors: {errors}"
            )

            # All results should be identical
            assert len(results) == 10
            assert all(r == results[0] for r in results), (
                f"All threads should get same lock range: {results}"
            )

            # On Windows, should be the fixed value
            if os.name == 'nt':
                assert results[0] == 0xFFFF0000
