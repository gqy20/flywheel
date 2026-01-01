"""Test for Issue #371: Windows file lock range calculation race condition.

This test verifies that _get_file_lock_range_from_handle uses os.fstat
instead of os.path.getsize to avoid race conditions when the file is
replaced (symlink attacks).
"""

import os
import tempfile
import pytest

from flywheel.storage import Storage


class TestFileLockRangeFromHandle:
    """Test _get_file_lock_range_from_handle uses file descriptor, not path."""

    def test_uses_file_descriptor_not_path(self):
        """Verify that the method uses os.fstat (file descriptor) not os.path.getsize.

        This test creates a file and ensures that the method can get the file size
        using the file descriptor even if the file path becomes invalid (simulating
        a race condition where the file is replaced).

        The fix uses os.fstat(file_handle.fileno()).st_size instead of
        os.path.getsize(file_handle.name).
        """
        # Create a temporary file with known content
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
            tmp.write('{"todos": [], "next_id": 1, "metadata": {"checksum": "abc"}}')
            tmp_path = tmp.name

        try:
            # Open the file for reading
            with open(tmp_path, 'r') as file_handle:
                # Get the file size using the storage method
                storage = Storage(path=tmp_path)

                # Call the method under test
                lock_range = storage._get_file_lock_range_from_handle(file_handle)

                # Verify the lock range is at least the minimum (4096 bytes)
                assert lock_range >= 4096, f"Lock range {lock_range} should be >= 4096"

                # Verify the actual file size is considered
                actual_size = os.fstat(file_handle.fileno()).st_size
                expected_range = max(actual_size, 4096)
                assert lock_range == expected_range, \
                    f"Lock range {lock_range} should match expected {expected_range}"

        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_file_descriptor_vs_path_difference(self):
        """Demonstrate the security difference between fstat and path.getsize.

        os.path.getsize(file_handle.name) uses the file path, which can change
        between opening the file and getting the size (TOCTOU race condition).

        os.fstat(file_handle.fileno()) uses the file descriptor, which always
        refers to the same open file, even if the path is replaced or renamed.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create initial file
            file_path = os.path.join(tmpdir, 'test.json')
            with open(file_path, 'w') as f:
                f.write('x' * 1000)  # Write 1000 bytes

            # Open the file
            with open(file_path, 'r') as file_handle:
                original_fd = file_handle.fileno()

                # Get size via file descriptor (safe - uses open file handle)
                size_via_fstat = os.fstat(original_fd).st_size
                assert size_via_fstat == 1000

                # Get size via path (potentially unsafe - path could change)
                size_via_path = os.path.getsize(file_handle.name)
                assert size_via_path == 1000

                # Now simulate the race: replace the file while it's still open
                os.unlink(file_path)
                with open(file_path, 'w') as f:
                    f.write('y' * 5000)  # Write 5000 bytes

                # Via file descriptor: still sees the original file (1000 bytes)
                size_via_fstat_after = os.fstat(original_fd).st_size
                assert size_via_fstat_after == 1000, \
                    "fstat should still see original file via fd"

                # Via path: sees the new file (5000 bytes) - POTENTIAL BUG!
                size_via_path_after = os.path.getsize(file_handle.name)
                assert size_via_path_after == 5000, \
                    "getsize sees the replaced file via path"

                # This demonstrates that using os.path.getsize(file_handle.name)
                # can lead to incorrect lock ranges if the file is replaced
                # between opening and calculating the lock range

                # The storage method should use the file descriptor approach
                storage = Storage(path=file_path)
                lock_range = storage._get_file_lock_range_from_handle(file_handle)

                # Should use the file descriptor size (original file: 1000 bytes)
                # Not the path-based size (replaced file: 5000 bytes)
                expected_size = os.fstat(file_handle.fileno()).st_size
                expected_range = max(expected_size, 4096)
                assert lock_range == expected_range, \
                    f"Lock range should be based on file descriptor, not path"

    def test_fstat_on_all_platforms(self):
        """Verify os.fstat works correctly on all platforms.

        This test ensures that os.fstat(file_handle.fileno()).st_size
        works correctly as a replacement for os.path.getsize(file_handle.name).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files of various sizes
            test_cases = [
                (0, "empty file"),
                (100, "small file"),
                (5000, "medium file"),
                (10000, "larger file"),
            ]

            for size, description in test_cases:
                file_path = os.path.join(tmpdir, f'test_{size}.json')
                with open(file_path, 'w') as f:
                    f.write('x' * size)

                # Verify both methods return the same size
                with open(file_path, 'r') as file_handle:
                    size_path = os.path.getsize(file_handle.name)
                    size_fstat = os.fstat(file_handle.fileno()).st_size

                    assert size_path == size_fstat, \
                        f"{description}: path and fstat should match (path={size_path}, fstat={size_fstat})"
                    assert size_fstat == size, \
                        f"{description}: fstat size should be {size}, got {size_fstat}"

    def test_windows_lock_range_minimum(self):
        """Test that Windows lock range has a minimum of 4096 bytes.

        This is documented behavior to ensure reasonable lock coverage
        for small files (Issue #346).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a very small file
            file_path = os.path.join(tmpdir, 'small.json')
            with open(file_path, 'w') as f:
                f.write('{}')  # Only 2 bytes

            storage = Storage(path=file_path)

            with open(file_path, 'r') as file_handle:
                lock_range = storage._get_file_lock_range_from_handle(file_handle)

                # Should be at least 4096, even for tiny files
                assert lock_range >= 4096, \
                    f"Lock range {lock_range} should be >= 4096 for small files"

                # Verify it's using the max of file size and 4096
                actual_size = os.fstat(file_handle.fileno()).st_size
                expected = max(actual_size, 4096)
                assert lock_range == expected, \
                    f"Lock range should be max(file_size, 4096)"
