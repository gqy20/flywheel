"""Regression tests for issue #6493: Race condition in _ensure_parent_directory.

Issue: TOCTOU race condition between exists() check and mkdir() with exist_ok=False
allows concurrent processes to trigger FileExistsError.

These tests verify the race condition is fixed by using exist_ok=True.
"""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import _ensure_parent_directory


def test_ensure_parent_directory_race_condition_with_mock(tmp_path) -> None:
    """Test that _ensure_parent_directory handles race condition gracefully.

    This test simulates the TOCTOU race condition by mocking mkdir to raise
    FileExistsError, which would happen if another process creates the directory
    between our exists() check and mkdir() call.

    Before fix: This test would fail with uncaught FileExistsError
    After fix: The function should handle this gracefully with exist_ok=True
    """
    # Create a path where parent doesn't exist
    file_path = tmp_path / "subdir" / "file.json"

    # The parent directory doesn't exist initially
    assert not file_path.parent.exists()

    # Simulate race condition: another process creates the directory
    # between our exists() check and mkdir() call
    original_mkdir = Path.mkdir

    def mock_mkdir_with_race(self, parents=False, exist_ok=False):
        # Simulate another process creating the directory right before our mkdir
        if not exist_ok and not self.exists():
            # Create the directory to simulate the race
            original_mkdir(self, parents=parents, exist_ok=True)
            # Now our mkdir should fail with FileExistsError if exist_ok=False
            raise FileExistsError(
                f"[Errno 17] File exists: '{self}' (simulated race condition)"
            )
        # With exist_ok=True, this should succeed
        return original_mkdir(self, parents=parents, exist_ok=True)

    with patch.object(Path, "mkdir", mock_mkdir_with_race):
        # This should NOT raise FileExistsError after the fix
        # The fix uses exist_ok=True which handles the race condition
        _ensure_parent_directory(file_path)

    # Parent directory should exist now
    assert file_path.parent.exists()


def test_ensure_parent_directory_concurrent_calls(tmp_path) -> None:
    """Test that concurrent calls to _ensure_parent_directory don't raise errors.

    Multiple processes calling _ensure_parent_directory concurrently should all
    succeed without raising FileExistsError.

    This is a more realistic test that exercises the actual race condition.
    """
    file_path = tmp_path / "deeply" / "nested" / "dir" / "file.json"
    errors = multiprocessing.Manager().list()

    def worker(worker_id: int) -> None:
        """Worker that calls _ensure_parent_directory."""
        try:
            # Small stagger to increase race condition likelihood
            time.sleep(0.001 * (worker_id % 3))
            _ensure_parent_directory(file_path)
        except Exception as e:
            errors.append((worker_id, str(e)))

    # Run multiple workers concurrently
    num_workers = 10
    processes = []
    for i in range(num_workers):
        p = multiprocessing.Process(target=worker, args=(i,))
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join(timeout=10)

    # Verify no errors occurred
    assert len(errors) == 0, f"Workers encountered errors: {list(errors)}"

    # Directory should exist
    assert file_path.parent.exists()


def test_ensure_parent_directory_file_as_parent_still_fails(tmp_path) -> None:
    """Verify that file-as-directory validation still works after the fix.

    The fix should only change the exist_ok behavior, not the file-as-directory
    validation that happens before the mkdir call.
    """
    # Create a file where we expect a directory
    blocking_file = tmp_path / "blocking.txt"
    blocking_file.write_text("I am a file")

    # Try to create a path that would require the file to be a directory
    file_path = blocking_file / "subdir" / "file.json"

    # Should raise ValueError about file vs directory confusion
    with pytest.raises(ValueError, match=r"(exists as a file|not a directory)"):
        _ensure_parent_directory(file_path)


def test_ensure_parent_directory_normal_creation(tmp_path) -> None:
    """Test normal case: _ensure_parent_directory creates missing directories."""
    file_path = tmp_path / "new" / "nested" / "dir" / "file.json"

    # Parent shouldn't exist
    assert not file_path.parent.exists()

    # Should create the directory
    _ensure_parent_directory(file_path)

    # Parent should exist now
    assert file_path.parent.exists()
    assert file_path.parent.is_dir()
