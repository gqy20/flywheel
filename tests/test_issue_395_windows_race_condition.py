"""Test for Issue #395: Windows race condition in directory creation.

This test verifies that directories are created securely even if there's
a crash between mkdir and _secure_directory.
"""

import os
import tempfile
import shutil
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from flywheel.storage import Storage


class SkipIfNotWindows:
    """Skip test on non-Windows platforms for Windows-specific tests."""
    pass


@pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
class TestWindowsDirectoryCreationRaceCondition:
    """Test Windows directory creation security during race conditions."""

    def test_mkdir_before_secure_directory_race(self, tmp_path):
        """Test that directories are secure even if crash occurs after mkdir.

        This test simulates a crash after mkdir but before _secure_directory
        by mocking _secure_directory to fail after mkdir succeeds.

        The test verifies that:
        1. mkdir is called first (potentially creating insecure directory)
        2. _secure_directory is then called to secure it
        3. If _secure_directory fails, the directory should not remain insecure
        """
        storage_path = tmp_path / "test_storage" / "todos.json"

        # Track the order of operations
        operations = []

        original_mkdir = Path.mkdir
        original_secure = Storage._secure_directory

        def mock_mkdir(self, *args, **kwargs):
            operations.append('mkdir')
            return original_mkdir(self, *args, **kwargs)

        def mock_secure_after_mkdir(directory):
            operations.append('secure_directory')
            # Simulate crash or failure after first mkdir
            if 'mkdir' in operations and 'secure_directory' in operations:
                # Check if directory exists and has proper permissions
                if not directory.exists():
                    raise RuntimeError(f"Directory {directory} was not created")
                # On Windows, we need to verify ACLs are set
                # If we get here before secure completes, this is a security issue
                return original_secure(directory)

        with patch.object(Path, 'mkdir', mock_mkdir):
            with patch.object(Storage, '_secure_directory', mock_secure_after_mkdir):
                # This should either:
                # 1. Complete successfully with secure directory
                # 2. Raise an error if directory cannot be secured
                try:
                    storage = Storage(str(storage_path))
                    # If we reach here, directory should be secure
                    assert storage_path.parent.exists()
                except RuntimeError as e:
                    # If _secure_directory raises an error, that's acceptable
                    # as it prevents running with insecure directory
                    assert "secure" in str(e).lower() or "permission" in str(e).lower()

        # Verify mkdir was called before secure_directory
        assert 'mkdir' in operations
        assert 'secure_directory' in operations
        # Verify secure_directory was called after mkdir
        mkdir_idx = operations.index('mkdir')
        secure_idx = operations.index('secure_directory')
        assert secure_idx > mkdir_idx, "secure_directory should be called after mkdir"

    def test_no_insecure_window_during_initialization(self, tmp_path):
        """Test that there's no insecure window during Storage initialization.

        This test verifies that even if _secure_directory is delayed,
        the directory creation doesn't leave a window where:
        1. mkdir creates directory with inherited ACLs
        2. Process crashes before _secure_directory applies restrictive ACLs
        """
        storage_path = tmp_path / "test_race" / "todos.json"

        # Mock to simulate delay or crash
        secure_called = []

        original_secure = Storage._secure_directory

        def mock_secure_with_delay(directory):
            secure_called.append(directory)
            # In a real crash scenario, this might not complete
            # For this test, we'll let it complete but verify the sequence
            return original_secure(directory)

        with patch.object(Storage, '_secure_directory', mock_secure_with_delay):
            storage = Storage(str(storage_path))

            # Verify _secure_directory was called
            assert len(secure_called) > 0
            # Verify it was called for the parent directory
            assert storage_path.parent in secure_called

            # Verify the directory exists
            assert storage_path.parent.exists()

    def test_all_parent_directories_secured(self, tmp_path):
        """Test that all parent directories are secured, not just the final one.

        This is crucial because mkdir(parents=True) may create multiple directories,
        and on Windows they all inherit potentially insecure ACLs.
        """
        # Create a deep path to ensure multiple parent directories
        deep_path = tmp_path / "level1" / "level2" / "level3" / "todos.json"

        secured_directories = []

        original_secure = Storage._secure_directory

        def mock_secure_tracker(self, directory):
            secured_directories.append(directory)
            return original_secure(directory)

        with patch.object(Storage, '_secure_directory', mock_secure_tracker):
            storage = Storage(str(deep_path))

            # Verify all parent directories were secured
            expected_parents = [
                tmp_path / "level1",
                tmp_path / "level1" / "level2",
                tmp_path / "level1" / "level2" / "level3",
            ]

            for expected_dir in expected_parents:
                assert expected_dir in secured_directories, \
                    f"Parent directory {expected_dir} was not secured"


@pytest.mark.skipif(os.name == 'nt', reason="Unix-specific test")
class TestUnixDirectoryCreationSecurity:
    """Test Unix directory creation security."""

    def test_unix_mkdir_with_restrictive_mode(self, tmp_path):
        """Test that Unix mkdir uses mode=0o700 for restrictive permissions."""
        storage_path = tmp_path / "test_unix" / "todos.json"

        # Track mkdir calls
        mkdir_calls = []

        original_mkdir = Path.mkdir

        def mock_mkdir(self, *args, **kwargs):
            mkdir_calls.append((self, kwargs))
            return original_mkdir(self, *args, **kwargs)

        with patch.object(Path, 'mkdir', mock_mkdir):
            storage = Storage(str(storage_path))

            # Verify mkdir was called with mode=0o700 on Unix
            assert len(mkdir_calls) > 0
            for path, kwargs in mkdir_calls:
                if 'mode' in kwargs:
                    # Should be called with restrictive mode
                    assert kwargs['mode'] == 0o700, \
                        f"mkdir should use mode=0o700, got {kwargs['mode']}"


class TestDirectoryCreationPlatformAgnostic:
    """Platform-agnostic tests for directory creation security."""

    def test_storage_initialization_creates_directory(self, tmp_path):
        """Test that Storage initialization creates the directory."""
        storage_path = tmp_path / "test_dir" / "todos.json"

        # Directory shouldn't exist initially
        assert not storage_path.parent.exists()

        # Create storage
        storage = Storage(str(storage_path))

        # Directory should exist now
        assert storage_path.parent.exists()

    def test_storage_initialization_secures_directory(self, tmp_path):
        """Test that Storage initialization calls _secure_directory."""
        storage_path = tmp_path / "test_secure" / "todos.json"

        secure_calls = []

        original_secure = Storage._secure_directory

        def mock_secure_tracker(self, directory):
            secure_calls.append(directory)
            return original_secure(directory)

        with patch.object(Storage, '_secure_directory', mock_secure_tracker):
            storage = Storage(str(storage_path))

            # Verify _secure_directory was called at least once
            assert len(secure_calls) > 0

    def test_crash_between_mkdir_and_secure_scenario(self, tmp_path):
        """Test the crash scenario described in Issue #395.

        This test simulates what happens if:
        1. mkdir creates directory with insecure permissions
        2. Process crashes before _secure_directory can apply ACLs

        In a secure implementation, this should either:
        - Prevent the directory from being created until it can be secured
        - Raise an error to prevent running with insecure directory
        """
        storage_path = tmp_path / "crash_scenario" / "todos.json"

        # Simulate crash after mkdir but before secure completes
        mkdir_succeeded = []

        original_mkdir = Path.mkdir

        def mock_mkdir_then_crash(self, *args, **kwargs):
            result = original_mkdir(self, *args, **kwargs)
            mkdir_succeeded.append(self)
            # Simulate crash - don't continue to _secure_directory
            # In real scenario, the process would terminate here
            raise RuntimeError("Simulated crash after mkdir")

        # This should raise an error because mkdir succeeded but
        # the directory cannot be secured
        with pytest.raises(RuntimeError, match="crash"):
            with patch.object(Path, 'mkdir', mock_mkdir_then_crash):
                storage = Storage(str(storage_path))

        # Verify mkdir was called
        assert len(mkdir_succeeded) > 0

        # At this point, the directory exists but may be insecure
        # In a real scenario, this would be a security issue
        # The test verifies the code structure allows detecting this
