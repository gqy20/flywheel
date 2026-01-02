"""Test for Issue #481 - Race condition in directory creation and security.

This test verifies that when a directory is created by another process,
the system ALWAYS verifies and fixes permissions, rather than assuming
the directory is secure.
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest import mock
import pytest

from flywheel.storage import Storage


class TestDirectoryRaceCondition:
    """Test that directory creation race conditions are handled securely."""

    def test_directory_created_by_other_process_gets_secured(self):
        """Test that a directory created by another process gets secured.

        This simulates a race condition where another process creates
        the directory with insecure permissions between our existence
        check and creation attempt. The system should always verify
        and secure the directory, never assume it's safe.
        """
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test_subdir" / "todos.json"

            # Pre-create the parent directory with INSECURE permissions
            # This simulates another process creating it
            parent_dir = test_path.parent
            parent_dir.mkdir(parents=True, exist_ok=True)

            if os.name != 'nt':  # Unix-like systems
                # Set deliberately insecure permissions (world-readable/writable)
                parent_dir.chmod(0o777)

            # Verify the directory has insecure permissions
            if os.name != 'nt':
                stat_info = parent_dir.stat()
                mode = stat_info.st_mode & 0o777
                # On Unix, the directory should be insecure (0o777)
                assert mode == 0o777, f"Expected insecure 0o777, got {oct(mode)}"

            # Mock mkdir to raise FileExistsError to simulate race condition
            original_mkdir = Path.mkdir

            def mock_mkdir_that_raises(self, *args, **kwargs):
                """Raise FileExistsError to simulate competing process."""
                # Only raise for the specific directory we're testing
                if self == parent_dir or self in parent_dir.parents:
                    raise FileExistsError(f"Directory {self} already exists")
                # For other directories, use original mkdir
                return original_mkdir(self, *args, **kwargs)

            # Patch Path.mkdir to simulate the race condition
            with mock.patch.object(Path, 'mkdir', mock_mkdir_that_raises):
                # Create Storage - this should handle the FileExistsError
                # and SECURE the directory, not just assume it's safe
                storage = Storage(str(test_path))

                try:
                    # Verify the directory was created
                    assert parent_dir.exists(), "Parent directory should exist"

                    # On Unix: Verify permissions were corrected to 0o700
                    if os.name != 'nt':
                        stat_info = parent_dir.stat()
                        mode = stat_info.st_mode & 0o777
                        # The directory should now be secure (0o700)
                        assert mode == 0o700, (
                            f"Expected secure permissions 0o700 after handling "
                            f"race condition, got {oct(mode)}. "
                            f"This indicates the system did not verify and fix "
                            f"permissions when FileExistsError was caught."
                        )

                    # On Windows: We can't easily verify ACLs without pywin32 APIs,
                    # but the fact that no exception was raised indicates success
                    # (Windows security would raise RuntimeError if ACLs failed)
                finally:
                    # Cleanup
                    storage.close()

    def test_create_and_secure_directories_always_verifies(self):
        """Test _create_and_secure_directories always verifies on FileExistsError.

        This is a more direct unit test of the _create_and_secure_directories
        method to ensure it ALWAYS calls _secure_directory when catching
        FileExistsError, not just checks permissions and skips.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_dir"

            # Create directory with INSECURE permissions
            test_dir.mkdir(parents=True, exist_ok=True)

            if os.name != 'nt':  # Unix-like systems
                # Set insecure permissions
                test_dir.chmod(0o777)

            # Track whether _secure_directory was called
            secure_directory_called = []

            def track_secure_directory(self, directory):
                """Track calls to _secure_directory."""
                secure_directory_called.append(directory)
                # Call the original method
                import flywheel.storage
                original_method = flywheel.storage.Storage._secure_directory
                return original_method(self, directory)

            # Patch _secure_directory to track calls
            with mock.patch.object(
                Storage,
                '_secure_directory',
                track_secure_directory
            ):
                storage = Storage(str(test_dir / "todos.json"))

                try:
                    # Verify _secure_directory was called for our test directory
                    # or one of its parents
                    was_called = any(
                        test_dir in secure_directory_called or
                        any(str(test_dir) in str(p) for p in secure_directory_called)
                    )
                    assert was_called, (
                        f"_secure_directory was not called for {test_dir}. "
                        f"This indicates the system did not verify permissions "
                        f"when FileExistsError was caught."
                    )
                finally:
                    storage.close()

    def test_multiple_race_conditions_with_retries(self):
        """Test that multiple race conditions are handled with retries.

        Simulates a scenario where multiple processes are competing
        to create the same directory, causing multiple FileExistsError
        exceptions. The system should retry and eventually succeed.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "race" / "todos.json"

            # Counter to simulate multiple race conditions
            attempt_count = [0]
            max_race_conditions = 2  # Simulate 2 race conditions

            def mock_mkdir_with_races(self, *args, **kwargs):
                """Simulate multiple race conditions."""
                if self in [test_path.parent] + list(test_path.parent.parents):
                    attempt_count[0] += 1
                    if attempt_count[0] <= max_race_conditions:
                        # Simulate race condition
                        raise FileExistsError(f"Race condition #{attempt_count[0]}")
                # After retries, actually create the directory
                return Path.mkdir(self, *args, **kwargs)

            with mock.patch.object(Path, 'mkdir', mock_mkdir_with_races):
                # This should handle the race conditions and succeed
                storage = Storage(str(test_path))

                try:
                    # Verify success
                    assert test_path.parent.exists()
                    assert attempt_count[0] > max_race_conditions, (
                        f"Expected {max_race_conditions} race conditions to be handled"
                    )
                finally:
                    storage.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
