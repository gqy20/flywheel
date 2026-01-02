"""Test for Issue #476 - Race condition in _secure_all_parent_directories.

This test verifies that _secure_all_parent_directories properly handles
the TOCTOU (Time-of-Check-Time-of-Use) race condition where a directory
might be created by another process between the existence check and the
securing operation.

The issue is that the current implementation checks if a directory exists
before securing it, but doesn't handle the case where the directory is
created by another process between the check and the secure operation.
"""

import os
import tempfile
import threading
import time
from pathlib import Path
import pytest

from flywheel.storage import Storage


class TestRaceConditionInSecureAllParentDirectories:
    """Test that _secure_all_parent_directories handles race conditions."""

    def test_concurrent_directory_creation_during_securing(self):
        """Test race condition when directories are created concurrently.

        This test simulates a scenario where:
        1. _create_and_secure_directories is called and creates some directories
        2. Between _create_and_secure_directories and _secure_all_parent_directories,
           another process creates parent directories with insecure permissions
        3. _secure_all_parent_directories should secure these directories

        The test verifies that even if a directory is created with insecure
        permissions between the two calls, it gets secured properly.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a nested path that will trigger directory creation
            nested_path = Path(tmpdir) / "level1" / "level2" / "level3" / "todos.json"

            # Create the first level directory with insecure permissions
            level1 = Path(tmpdir) / "level1"
            level1.mkdir(mode=0o755)  # Insecure permissions (world-readable)

            # Verify it has insecure permissions
            stat_info = level1.stat()
            mode = stat_info.st_mode & 0o777
            assert mode == 0o755, f"Expected 0o755, got {mode:o}"

            # Now create a Storage instance
            # This should:
            # 1. Call _create_and_secure_directories which creates level2 and level3
            # 2. Call _secure_all_parent_directories which should secure level1
            storage = Storage(path=str(nested_path))

            # Verify that level1 now has secure permissions
            stat_info = level1.stat()
            mode = stat_info.st_mode & 0o777
            assert mode == 0o700, f"Expected secure permissions 0o700, got {mode:o}"

            # Verify that level2 and level3 also have secure permissions
            level2 = level1 / "level2"
            level3 = level2 / "level3"

            for directory in [level2, level3]:
                stat_info = directory.stat()
                mode = stat_info.st_mode & 0o777
                assert mode == 0o700, f"Expected secure permissions 0o700 for {directory}, got {mode:o}"

    def test_race_condition_with_concurrent_process(self):
        """Test TOCTOU race condition with simulated concurrent process.

        This test simulates a more realistic race condition where a directory
        is created by another process AFTER _create_and_secure_directories
        checks for its existence but BEFORE _secure_all_parent_directories
        can secure it.

        We simulate this by using threading to create a directory with
        insecure permissions in a narrow window.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "level1" / "level2" / "todos.json"

            # Flag to control when the thread should create the directory
            create_directory = threading.Event()
            directory_created = threading.Event()

            def create_insecure_directory():
                """Thread function to create a directory with insecure permissions."""
                # Wait for the main thread to signal
                create_directory.wait()

                # Create the directory with insecure permissions
                level1 = Path(tmpdir) / "level1"
                if not level1.exists():
                    level1.mkdir(mode=0o755)  # Insecure permissions

                directory_created.set()

            # Start the thread
            thread = threading.Thread(target=create_insecure_directory)
            thread.start()

            # Signal the thread to create the directory
            create_directory.set()

            # Wait a bit to ensure the directory is created
            directory_created.wait(timeout=1.0)

            # Now create Storage - it should secure the directory
            storage = Storage(path=str(nested_path))

            # Wait for thread to complete
            thread.join(timeout=2.0)

            # Verify that level1 now has secure permissions
            level1 = Path(tmpdir) / "level1"
            stat_info = level1.stat()
            mode = stat_info.st_mode & 0o777
            assert mode == 0o700, f"Expected secure permissions 0o700, got {mode:o}"

    def test_secure_all_parent_directories_handles_existing_insecure_dirs(self):
        """Test that _secure_all_parent_directories secures existing insecure directories.

        This test verifies that if parent directories already exist with
        insecure permissions, _secure_all_parent_directories properly secures them.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "level1" / "level2" / "level3" / "todos.json"

            # Create all parent directories with insecure permissions
            level1 = Path(tmpdir) / "level1"
            level2 = level1 / "level2"
            level3 = level2 / "level3"

            for directory in [level1, level2, level3]:
                if not directory.exists():
                    directory.mkdir(mode=0o755)  # Insecure permissions

            # Verify they have insecure permissions
            for directory in [level1, level2, level3]:
                stat_info = directory.stat()
                mode = stat_info.st_mode & 0o777
                assert mode == 0o755, f"Expected 0o755 for {directory}, got {mode:o}"

            # Create Storage - it should secure all parent directories
            storage = Storage(path=str(nested_path))

            # Verify that all parent directories now have secure permissions
            for directory in [level1, level2, level3]:
                stat_info = directory.stat()
                mode = stat_info.st_mode & 0o777
                assert mode == 0o700, f"Expected secure permissions 0o700 for {directory}, got {mode:o}"
