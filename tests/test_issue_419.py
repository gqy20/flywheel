"""Test for issue #419 - Windows directory creation race condition vulnerability.

This test verifies that the directory creation process handles race conditions
properly when multiple threads/processes attempt to create the same directory
simultaneously.
"""

import os
import tempfile
from pathlib import Path
import threading

import pytest

from flywheel.storage import Storage


def test_create_and_secure_directories_with_existing_directory():
    """Test that _create_and_secure_directories handles existing directory.

    This test verifies that when a directory already exists (simulating a race
    condition where another process created it), the method handles it gracefully
    by either accepting it if permissions are correct, or fixing permissions if
    they're wrong.

    This is a regression test for issue #419.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a temporary storage to access the method
        temp_storage_path = Path(tmpdir) / "temp" / "todos.json"
        temp_storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage = Storage(str(temp_storage_path))

        # Create a directory that already exists
        test_dir = Path(tmpdir) / "test_existing" / "nested"
        test_dir.mkdir(parents=True, exist_ok=True)

        # Set wrong permissions on Unix (simulate security issue)
        if os.name != 'nt':
            test_dir.chmod(0o755)  # Too permissive

        # This should handle the existing directory and fix permissions
        try:
            storage._create_and_secure_directories(test_dir)

            # Verify directory exists
            assert test_dir.exists()

            # On Unix, verify permissions were corrected
            if os.name != 'nt':
                stat_info = test_dir.stat()
                mode = stat_info.st_mode & 0o777
                assert mode == 0o700, f"Expected 0o700, got {oct(mode)}"

        except FileExistsError:
            pytest.fail(
                "_create_and_secure_directories should not raise FileExistsError "
                "when directory already exists"
            )
        except RuntimeError as e:
            # Security errors are acceptable
            if "secure" not in str(e).lower():
                raise


def test_concurrent_directory_creation_with_threads():
    """Test concurrent directory creation with multiple threads.

    This test creates multiple threads that attempt to create the same directory
    path simultaneously. The implementation should handle this race condition
    gracefully without raising FileExistsError.

    This is a regression test for issue #419.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "test_concurrent" / "todos.json"

        num_threads = 10
        errors = []
        successes = []

        def create_storage_thread(thread_id):
            """Try to create storage in a thread."""
            try:
                storage = Storage(str(test_path))
                successes.append(thread_id)
            except FileExistsError as e:
                # This is the bug - FileExistsError should be handled internally
                errors.append(("FileExistsError", str(e), thread_id))
            except RuntimeError as e:
                # RuntimeError related to security is acceptable
                if "secure" not in str(e).lower():
                    errors.append(("RuntimeError", str(e), thread_id))
            except Exception as e:
                errors.append((type(e).__name__, str(e), thread_id))

        # Create threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=create_storage_thread, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check for FileExistsError - this indicates the race condition bug
        file_exists_errors = [e for e in errors if e[0] == "FileExistsError"]

        if file_exists_errors:
            pytest.fail(
                f"Race condition vulnerability detected: {len(file_exists_errors)} "
                f"threads encountered FileExistsError. This indicates that "
                f"directory creation does not properly handle the case where "
                f"a directory is created by another process between the check "
                f"and creation attempt."
            )

        # At least some threads should succeed
        assert len(successes) > 0, "At least one thread should succeed"


def test_storage_initialization_with_race_condition():
    """Test Storage initialization when parent directory already exists.

    This simulates a race condition where the parent directory is created
    between the existence check and the creation attempt.

    This is a regression test for issue #419.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # On Unix, test the regular initialization
        if os.name != 'nt':
            test_path = Path(tmpdir) / "test_storage_race" / "todos.json"

            # Create parent directory first (simulates race condition)
            test_path.parent.mkdir(parents=True, exist_ok=True)

            # Set wrong permissions
            test_path.parent.chmod(0o755)

            try:
                # This should handle existing directory and fix permissions
                storage = Storage(str(test_path))

                # Verify storage was created successfully
                assert storage.path == test_path

                # Verify permissions were corrected
                stat_info = test_path.parent.stat()
                mode = stat_info.st_mode & 0o777
                assert mode == 0o700, f"Expected 0o700, got {oct(mode)}"

            except FileExistsError:
                pytest.fail(
                    "Storage initialization should not raise FileExistsError "
                    "when parent directory already exists"
                )
            except RuntimeError as e:
                # Security errors are acceptable
                if "secure" not in str(e).lower():
                    raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
