"""Regression tests for issue #6171: TOCTOU race condition in _ensure_parent_directory.

Issue: There is a Time-Of-Check-To-Time-Use (TOCTOU) race between checking
if parent exists and calling mkdir. An attacker could create a directory
at the parent path between the check and mkdir, causing mkdir to fail
when exist_ok=False.

The fix should use exist_ok=True and handle the case where the directory
is created concurrently.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from flywheel.storage import _ensure_parent_directory


def test_toctou_race_condition_concurrent_directory_creation(tmp_path) -> None:
    """Issue #6171: mkdir should succeed even if directory is created concurrently.

    This test simulates the TOCTOU race by creating the parent directory
    between the exists() check and mkdir() call.

    Before fix: mkdir with exist_ok=False raises FileExistsError
    After fix: mkdir with exist_ok=True succeeds silently
    """
    # Create a path that requires a new parent directory
    db_path = tmp_path / "newdir" / "subdir" / "db.json"
    parent = db_path.parent

    # Ensure parent doesn't exist yet
    assert not parent.exists()

    # We'll simulate the race condition by monkey-patching mkdir
    # to first create the directory, then call the original mkdir
    original_mkdir = Path.mkdir
    race_triggered = False

    def race_mkdir(self, *args, **kwargs):
        nonlocal race_triggered
        # If this is the parent directory we're creating, create it first
        # to simulate another process creating it between exists() and mkdir()
        if self == parent and not self.exists():
            # Create the directory (simulating concurrent creation)
            original_mkdir(self, parents=True, exist_ok=True)
            race_triggered = True
        # Now call the original mkdir
        return original_mkdir(self, *args, **kwargs)

    # Monkey-patch Path.mkdir
    Path.mkdir = race_mkdir

    try:
        # This should NOT raise an error - the directory already exists
        # but that's fine because we should use exist_ok=True
        _ensure_parent_directory(db_path)

        # Verify the race was actually triggered
        assert race_triggered, "Race condition simulation should have been triggered"

        # Verify parent directory exists
        assert parent.exists()
        assert parent.is_dir()
    finally:
        # Restore original mkdir
        Path.mkdir = original_mkdir


def test_toctou_race_condition_multiple_threads(tmp_path) -> None:
    """Issue #6171: Multiple threads creating same directory should all succeed.

    This tests that the function handles concurrent calls properly
    by using exist_ok=True.
    """
    db_path = tmp_path / "shared" / "db.json"
    errors = []
    success_count = [0]  # Use list for mutability in nested function

    def call_ensure_parent():
        try:
            _ensure_parent_directory(db_path)
            success_count[0] += 1
        except Exception as e:
            errors.append(e)

    # Create multiple threads that will all try to create the same directory
    threads = [threading.Thread(target=call_ensure_parent) for _ in range(10)]

    # Start all threads
    for t in threads:
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    # All threads should succeed (no FileExistsError)
    assert len(errors) == 0, f"All threads should succeed, but got errors: {errors}"
    assert success_count[0] == 10, "All 10 threads should succeed"

    # Directory should exist
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()


def test_ensure_parent_directory_idempotent(tmp_path) -> None:
    """Issue #6171: Calling _ensure_parent_directory multiple times should be safe.

    This verifies that exist_ok=True makes the function idempotent.
    """
    db_path = tmp_path / "mydir" / "db.json"

    # Call multiple times
    _ensure_parent_directory(db_path)
    _ensure_parent_directory(db_path)
    _ensure_parent_directory(db_path)

    # Should succeed without errors
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()
