"""Test for race condition in directory creation logic (Issue #486).

This test verifies that there is no race condition window between
_create_and_secure_directories and _secure_all_parent_directories.

The security issue is that if a directory is created by another process
AFTER _create_and_secure_directories completes but BEFORE _secure_all_parent_directories
runs, the directory might have insecure permissions.

The fix should ensure these two operations are atomic or combined.
"""

import os
import tempfile
import stat
import threading
import time
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_no_race_condition_between_directory_creation_and_securing():
    """Test that there's no race condition between directory creation and securing.

    This test simulates a scenario where another process creates a directory
    with insecure permissions between the _create_and_secure_directories call
    and the _secure_all_parent_directories call.

    The test uses threading to simulate concurrent access and verifies that
    all directories end up with secure permissions regardless of timing.

    Ref: Issue #486
    """
    if os.name == 'nt':  # Skip on Windows (different security model)
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        original_umask = os.umask(0)

        try:
            # Set a permissive umask
            os.umask(0o000)

            # Create a nested path
            base_path = Path(tmpdir) / "race_test"
            storage_path = base_path / "nested" / "todos.json"

            # Flag to control the race condition simulation
            create_insecure_dir = threading.Event()
            insecure_dir_created = threading.Event()

            # Track if we patched _secure_all_parent_directories
            patching_active = threading.Event()

            # Original method
            original_secure_all_parents = Storage._secure_all_parent_directories

            def delayed_secure_all_parents(self, directory):
                """Patched version that waits to simulate race condition."""
                # Signal that we're in _secure_all_parent_directories
                patching_active.set()

                # Wait for the signal to proceed
                create_insecure_dir.wait(timeout=5.0)

                # Call the original method
                return original_secure_all_parents(self, directory)

            def create_insecure_directory_concurrently():
                """Create a directory with insecure permissions concurrently."""
                # Wait until we're in the gap between creation and securing
                patching_active.wait(timeout=5.0)

                # Create a directory with insecure permissions
                test_dir = base_path / "concurrent_dir"
                test_dir.mkdir(mode=0o777, exist_ok=True)

                # Signal that we created the directory
                insecure_dir_created.set()

                # Allow the original thread to proceed
                create_insecure_dir.set()

            # Start the concurrent thread
            concurrent_thread = threading.Thread(target=create_insecure_directory_concurrently)
            concurrent_thread.start()

            # Patch the method to simulate the race condition
            with patch.object(Storage, '_secure_all_parent_directories', delayed_secure_all_parents):
                # Create storage - this will trigger the race condition scenario
                storage = Storage(str(storage_path))

            # Wait for the concurrent thread to finish
            concurrent_thread.join(timeout=10.0)

            # Verify that the concurrent directory was created
            concurrent_dir = base_path / "concurrent_dir"
            if concurrent_dir.exists():
                # The directory should have been secured despite the race condition
                stat_info = concurrent_dir.stat()
                mode = stat.S_IMODE(stat_info.st_mode)

                # This directory might not be secured by the current implementation
                # because it was created after the initial directory creation but
                # before _secure_all_parent_directories could run.
                # The test documents this vulnerability.
                if mode != 0o700:
                    # This is the BUG - the directory was created in the race window
                    # and was NOT secured by _secure_all_parent_directories
                    raise AssertionError(
                        f"Race condition vulnerability detected! Directory created during "
                        f"the gap between _create_and_secure_directories and "
                        f"_secure_all_parent_directories has insecure permissions {oct(mode)}. "
                        f"Expected 0o700. This demonstrates that there is a window where "
                        f"directories can be created with insecure permissions and NOT be "
                        f"secured by _secure_all_parent_directories."
                    )

            # Verify the main directories are secure
            parent_dir = storage_path.parent
            assert parent_dir.exists(), "Parent directory should exist"

            parent_stat = parent_dir.stat()
            parent_mode = stat.S_IMODE(parent_stat.st_mode)
            assert parent_mode == 0o700, (
                f"Parent directory has insecure permissions {oct(parent_mode)}. "
                f"Expected 0o700."
            )

        finally:
            os.umask(original_umask)


def test_directories_created_after_initial_call_are_secured():
    """Test that directories created after _create_and_secure_directories are still secured.

    This test verifies the fix for issue #486 by checking that the
    _secure_all_parent_directories method properly secures directories
    that were created after _create_and_secure_directories completed.

    The test creates a scenario where:
    1. _create_and_secure_directories completes
    2. A directory is created with insecure permissions
    3. _secure_all_parent_directories should secure it

    Ref: Issue #486
    """
    if os.name == 'nt':  # Skip on Windows
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        original_umask = os.umask(0)

        try:
            os.umask(0o000)

            # Create a nested path
            base_path = Path(tmpdir) / "secure_test"
            storage_path = base_path / "todos.json"

            # Create the base directory first
            base_path.mkdir(parents=True, exist_ok=True)

            # Manually create a directory with insecure permissions
            # This simulates a directory created by another process
            test_dir = base_path / "test_dir"
            test_dir.mkdir(mode=0o777)

            # Verify it's insecure
            stat_info = test_dir.stat()
            mode = stat.S_IMODE(stat_info.st_mode)
            assert mode == 0o777, f"Setup failed: directory mode is {oct(mode)}, not 0o777"

            # Now create Storage - this should secure all parent directories
            storage = Storage(str(storage_path))

            # Verify the test_dir is now secure
            # This is the fix - _secure_all_parent_directories should secure it
            stat_info_after = test_dir.stat()
            mode_after = stat.S_IMODE(stat_info_after.st_mode)

            assert mode_after == 0o700, (
                f"Directory created before Storage initialization still has "
                f"insecure permissions {oct(mode_after)} after Storage creation. "
                f"Expected 0o700. The _secure_all_parent_directories method should "
                f"secure ALL parent directories, even those created by other processes."
            )

        finally:
            os.umask(original_umask)


def test_combined_directory_creation_and_securing():
    """Test that directory creation and securing are combined/atomic.

    This test verifies that the implementation properly handles the case
    where directory creation and securing should be atomic operations.

    The test simulates rapid directory creation to ensure there's no window
    where directories exist with insecure permissions.

    Ref: Issue #486
    """
    if os.name == 'nt':  # Skip on Windows
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        original_umask = os.umask(0)

        try:
            os.umask(0o000)

            # Create multiple storage instances rapidly
            # This tests for race conditions in directory creation
            for i in range(10):
                storage_path = Path(tmpdir) / f"test_{i}" / "todos.json"

                # Create storage
                storage = Storage(str(storage_path))

                # Immediately verify security
                parent_dir = storage_path.parent
                parent_stat = parent_dir.stat()
                parent_mode = stat.S_IMODE(parent_stat.st_mode)

                assert parent_mode == 0o700, (
                    f"Iteration {i}: Directory has insecure permissions "
                    f"{oct(parent_mode)} immediately after creation. "
                    f"Expected 0o700. This indicates a race condition."
                )

        finally:
            os.umask(original_umask)


if __name__ == "__main__":
    # Run tests
    try:
        test_no_race_condition_between_directory_creation_and_securing()
        print("✓ test_no_race_condition_between_directory_creation_and_securing passed")
    except AssertionError as e:
        print(f"✗ test_no_race_condition_between_directory_creation_and_securing failed: {e}")
        print("  This is EXPECTED - it demonstrates the race condition vulnerability.")

    test_directories_created_after_initial_call_are_secured()
    print("✓ test_directories_created_after_initial_call_are_secured passed")

    test_combined_directory_creation_and_securing()
    print("✓ test_combined_directory_creation_and_securing passed")

    print("\nAll tests completed!")
