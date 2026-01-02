"""Test for Issue #409 - Windows directory creation race condition.

This test verifies that directory creation is atomic and handles
race conditions properly when multiple processes/threads attempt
to create the same directory simultaneously.
"""

import os
import tempfile
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from flywheel.storage import Storage


def test_directory_creation_race_condition(monkeypatch, tmp_path):
    """Test that _create_and_secure_directories handles race conditions.

    This test simulates a race condition where multiple threads try to
    create the same directory simultaneously. The implementation should
    handle this gracefully with retry logic (Issue #409).

    The test patches the exist_ok parameter to simulate failures.
    """
    # Track how many times directory creation is attempted
    creation_attempts = []
    original_create_and_secure = Storage._create_and_secure_directories

    def mock_create_and_secure(self, target_directory):
        """Mock that simulates race conditions on first few attempts."""
        creation_attempts.append(str(target_directory))

        # Simulate race condition on first attempt
        # by raising an error as if directory was created by another thread
        if len(creation_attempts) <= 2:
            # Simulate the directory already existing (race condition)
            # This is what happens when another thread creates it between
            # our check and creation
            raise FileExistsError(f"[Errno 17] File exists: '{target_directory}'")

        # After retries, call the original method
        return original_create_and_secure(self, target_directory)

    # Apply the monkeypatch
    monkeypatch.setattr(
        Storage,
        '_create_and_secure_directories',
        mock_create_and_secure
    )

    # This should succeed after retries, even with initial failures
    # The retry mechanism should handle the FileExistsError
    try:
        storage = Storage(path=str(tmp_path / "todos.json"))
        # If we get here without exception, the retry logic worked
        assert True
    except FileExistsError:
        # If we get FileExistsError, the retry mechanism is NOT implemented
        # This is the failing state we want to detect
        pytest.fail(
            "_create_and_secure_directories does not have retry mechanism. "
            "It failed with FileExistsError instead of retrying."
        )


def test_concurrent_directory_creation(tmp_path):
    """Test concurrent directory creation from multiple threads.

    This test creates multiple Storage instances pointing to nested
    directories in the same parent tree from different threads.
    Without proper atomic operations and retry logic, this would fail.
    """
    results = []
    errors = []

    def create_storage(thread_id):
        """Create a Storage instance in a thread."""
        try:
            # Each thread tries to create a nested directory
            # All threads share some common parent directories
            thread_path = tmp_path / f"thread_{thread_id}" / "nested" / "todos.json"
            storage = Storage(path=str(thread_path))
            results.append(thread_id)
            return True
        except Exception as e:
            errors.append((thread_id, str(e)))
            return False

    # Create multiple threads that all try to create directories
    # in the same parent tree simultaneously
    num_threads = 10
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(create_storage, i) for i in range(num_threads)]
        outcomes = [f.result() for f in as_completed(futures)]

    # All threads should succeed
    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert len(results) == num_threads


def test_directory_creation_idempotency(tmp_path):
    """Test that _create_and_secure_directories is idempotent.

    Calling the method multiple times on the same directory should
    not cause errors - it should recognize that the directory
    already exists and is properly secured.
    """
    # Create a directory
    storage_path = tmp_path / "test" / "nested" / "todos.json"
    storage1 = Storage(path=str(storage_path))

    # Call again on the same path - should not fail
    storage2 = Storage(path=str(storage_path))

    # Both should point to the same file
    assert storage1.path == storage2.path
    assert storage1.path.exists()


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
def test_windows_atomic_directory_creation(tmp_path):
    """Test that Windows uses atomic directory creation.

    On Windows, win32file.CreateDirectory should be used with a
    security descriptor to eliminate the time window between
    directory creation and ACL application (Issue #400).
    """
    # This test verifies the implementation uses win32file
    # We can't directly test the atomicity, but we can verify
    # the directory is created with correct permissions

    storage_path = tmp_path / "secure_dir" / "todos.json"
    storage = Storage(path=str(storage_path))

    # Verify the directory was created
    assert storage_path.parent.exists()

    # On Windows, verify pywin32 was used
    if os.name == 'nt':
        try:
            import win32security
            import win32con

            # Try to read the security descriptor
            sd = win32security.GetNamedSecurityInfo(
                str(storage_path.parent),
                win32security.SE_FILE_OBJECT,
                win32security.OWNER_SECURITY_INFORMATION |
                win32security.DACL_SECURITY_INFORMATION
            )

            # Verify it has a DACL (access control list)
            dacl = sd.GetSecurityDescriptorDacl()
            assert dacl is not None, "Directory should have a DACL"

        except ImportError:
            pytest.skip("pywin32 not installed")
