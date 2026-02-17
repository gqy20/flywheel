"""Regression tests for issue #3907: TOCTOU race condition in _ensure_parent_directory.

Issue: The _ensure_parent_directory function has a TOCTOU (Time-Of-Check-To-Time-Of-Use)
race condition window between checking parent paths (line 35-40) and creating
directories (line 43-50).

Attack scenario:
1. Thread A calls _ensure_parent_directory for /path/to/newdir/file.json
2. Thread A checks that all parents are valid (or don't exist)
3. Attacker/Thread B creates a file at /path/to/newdir between check and mkdir
4. Thread A's mkdir fails with FileExistsError but error message may be unclear

Key improvement needed:
- Use os.makedirs with exist_ok=True to handle concurrent creation safely
- Catch FileExistsError and distinguish 'file exists' from 'directory exists'
- Provide clear error messages for path conflicts

These tests verify the fix properly handles race conditions and provides clear errors.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import _ensure_parent_directory


def test_toctou_race_condition_clear_error_message(tmp_path) -> None:
    """Issue #3907: Error message should clearly indicate path conflict type.

    When a TOCTOU race condition occurs, the error message should distinguish
    between 'path component is a file' vs 'directory already exists'.
    """
    # Pre-create a file where a directory is expected
    blocking_file = tmp_path / "blocking_file"
    blocking_file.write_text("I block the path")

    target_path = blocking_file / "subdir" / "file.json"

    # Should raise with clear error about file vs directory conflict
    with pytest.raises((ValueError, OSError)) as exc_info:
        _ensure_parent_directory(target_path)

    error_msg = str(exc_info.value)
    # Should clearly indicate the conflict
    assert "file" in error_msg.lower() or "not a directory" in error_msg.lower()


def test_atomic_directory_creation_no_false_positives(tmp_path) -> None:
    """Issue #3907: Fix should not break normal directory creation.

    Ensure that the fix for TOCTOU doesn't break the happy path where
    directories are created normally.
    """
    target_path = tmp_path / "new" / "nested" / "path" / "file.json"

    # This should succeed without issues
    _ensure_parent_directory(target_path)

    # Verify directory was created
    assert target_path.parent.exists()
    assert target_path.parent.is_dir()


def test_concurrent_directory_creation_stress_test(tmp_path) -> None:
    """Issue #3907: Multiple threads creating same directory should be safe.

    Tests that concurrent calls to _ensure_parent_directory for the same path
    don't cause issues (exists_ok behavior should be safe).
    """
    target_path = tmp_path / "shared" / "path" / "file.json"
    errors = []
    success_count = [0]

    def create_directory():
        try:
            _ensure_parent_directory(target_path)
            success_count[0] += 1
        except Exception as e:
            errors.append(e)

    # Launch multiple threads trying to create the same directory
    threads = [threading.Thread(target=create_directory) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # At least some should succeed (race condition handling should be safe)
    # With proper fix, all should succeed
    assert len(errors) == 0, f"Errors during concurrent creation: {errors}"
    assert success_count[0] == 10


def test_makedirs_with_exist_ok_handles_concurrent_creation(tmp_path) -> None:
    """Issue #3907: Using os.makedirs with exist_ok=True should handle races safely.

    This tests the proposed fix: using os.makedirs with exist_ok=True and
    catching FileExistsError to provide clear error messages.
    """
    target_path = tmp_path / "race" / "test" / "file.json"
    parent = target_path.parent

    # First call should succeed
    _ensure_parent_directory(target_path)
    assert parent.is_dir()

    # Second call (directory now exists) should also succeed
    # This tests exist_ok=True behavior
    _ensure_parent_directory(target_path)
    assert parent.is_dir()


def test_error_distinguishes_file_vs_directory_exists(tmp_path) -> None:
    """Issue #3907: Error should distinguish 'file exists' from 'directory exists'.

    When path creation fails:
    - If a FILE exists at the path: should indicate file/directory conflict
    - If a DIRECTORY exists: should succeed (directory already there)
    """
    # Create a file where we need a directory
    blocking_file = tmp_path / "blocker"
    blocking_file.write_text("I am a file")

    target_path = blocking_file / "subpath" / "file.json"

    # This should fail with a clear error about file vs directory
    with pytest.raises((ValueError, OSError)) as exc_info:
        _ensure_parent_directory(target_path)

    # The error should mention the blocking file
    error_msg = str(exc_info.value)
    assert "blocker" in error_msg or "file" in error_msg.lower()
