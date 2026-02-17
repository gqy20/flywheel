"""Regression test for issue #3923: TOCTOU race condition in _ensure_parent_directory.

This test verifies that concurrent calls to _ensure_parent_directory do not
fail due to the TOCTOU (Time-Of-Check-Time-Of-Use) race condition.

The bug: Between checking if parent.exists() (line 43) and calling
parent.mkdir(exist_ok=False) (line 45), another thread could create
the directory, causing an OSError/FileExistsError.

The fix: Change exist_ok=False to exist_ok=True since the file-as-directory
validation already happened at lines 35-40.
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import _ensure_parent_directory


def test_ensure_parent_directory_concurrent_calls_no_race(tmp_path: Path) -> None:
    """Regression test for #3923: concurrent calls should not raise OSError.

    Multiple threads calling _ensure_parent_directory on the same non-existent
    path should complete without errors. The race condition occurs when:
    1. Thread A checks parent.exists() -> False
    2. Thread B checks parent.exists() -> False
    3. Thread A creates directory with mkdir(exist_ok=False) -> success
    4. Thread B tries mkdir(exist_ok=False) -> FileExistsError!

    With the fix (exist_ok=True), step 4 succeeds because the directory
    already exists and that's acceptable.
    """
    # Use a path with a non-existent parent directory
    target_path = tmp_path / "level1" / "level2" / "file.json"

    # Number of concurrent threads to test with
    num_threads = 10
    errors: list[Exception] = []
    barrier = threading.Barrier(num_threads)

    def worker() -> None:
        """Worker that calls _ensure_parent_directory concurrently."""
        try:
            # Synchronize all threads to maximize race condition likelihood
            barrier.wait(timeout=5)
            _ensure_parent_directory(target_path)
        except Exception as e:
            errors.append(e)

    # Start all threads
    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    for t in threads:
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join(timeout=10)

    # Verify no errors occurred
    if errors:
        error_messages = [f"{type(e).__name__}: {e}" for e in errors]
        pytest.fail(
            "Concurrent _ensure_parent_directory calls raised errors:\n" + "\n".join(error_messages)
        )

    # Verify the directory was created
    assert target_path.parent.exists(), "Parent directory should exist"
    assert target_path.parent.is_dir(), "Parent should be a directory"


def test_ensure_parent_directory_single_thread_behavior_unchanged(
    tmp_path: Path,
) -> None:
    """Verify that single-threaded behavior remains unchanged after the fix.

    The fix should not change the behavior when called from a single thread:
    - Directories should be created when they don't exist
    - No errors should be raised
    """
    target_path = tmp_path / "newdir" / "subdir" / "file.json"

    # Parent should not exist yet
    assert not target_path.parent.exists()

    # Call should succeed and create the directory
    _ensure_parent_directory(target_path)

    # Verify directory was created
    assert target_path.parent.exists()
    assert target_path.parent.is_dir()


def test_ensure_parent_directory_existing_directory_ok(tmp_path: Path) -> None:
    """Verify that calling with an existing parent directory works.

    With exist_ok=True, calling _ensure_parent_directory when the directory
    already exists should not raise any errors.
    """
    target_path = tmp_path / "existing" / "file.json"

    # Create the parent directory first
    target_path.parent.mkdir(parents=True)

    # Directory exists
    assert target_path.parent.exists()

    # Calling again should not raise any error
    _ensure_parent_directory(target_path)

    # Directory should still exist
    assert target_path.parent.exists()


def test_ensure_parent_directory_file_as_directory_still_raises(
    tmp_path: Path,
) -> None:
    """Verify that file-as-directory validation still works after the fix.

    The file-as-directory check at lines 35-40 should still raise ValueError
    when a parent component is a file instead of a directory.
    """
    # Create a file where we expect a directory
    blocking_file = tmp_path / "blocking_file.json"
    blocking_file.write_text("I am a file, not a directory")

    # Try to use a path that requires blocking_file to be a directory
    target_path = blocking_file / "subdir" / "file.json"

    # Should raise ValueError (not OSError or FileExistsError)
    with pytest.raises(ValueError, match="exists as a file, not a directory"):
        _ensure_parent_directory(target_path)


def test_ensure_parent_directory_toctou_race_injected(tmp_path: Path) -> None:
    """Regression test for #3923: inject race condition to verify fix.

    This test simulates the exact TOCTOU race condition by:
    1. Mocking Path.exists() to return False for the target's parent
    2. Having a side effect that creates the directory after the exists() check
    3. Then mkdir() with exist_ok=False would fail

    With exist_ok=True in the fix, the mkdir() succeeds even if the
    directory was created between the check and the mkdir call.
    """
    import pathlib

    target_path = tmp_path / "racedir" / "file.json"
    parent = target_path.parent

    # Store original methods
    original_exists = Path.exists

    # Track call count to inject race on specific path
    call_count = 0
    race_injected = False

    def racing_exists(self: Path) -> bool:
        """Mock exists that injects a race for our target parent path."""
        nonlocal call_count, race_injected

        # Only inject race for the specific parent path we're testing
        if self == parent:
            call_count += 1
            result = original_exists(self)

            # On first call, if directory doesn't exist, create it before returning
            # This simulates another thread creating the directory between the
            # exists() check and the mkdir() call
            if not result and call_count == 1 and not race_injected:
                race_injected = True
                parent.mkdir(parents=True)
                return False  # Return False to trigger mkdir path

            return result

        # For all other paths, use original behavior
        return original_exists(self)

    # Patch Path.exists globally to inject the race
    with patch.object(pathlib.Path, "exists", racing_exists):
        # With exist_ok=False (bug), this would raise FileExistsError wrapped in OSError
        # With exist_ok=True (fix), this should succeed
        _ensure_parent_directory(target_path)

    # Verify the race was actually injected
    assert race_injected, "Test setup error: race was not injected"

    # Verify the directory exists
    assert parent.exists()
    assert parent.is_dir()


def test_ensure_parent_directory_toctou_race_would_fail_without_fix(
    tmp_path: Path,
) -> None:
    """Test that demonstrates mkdir(exist_ok=False) fails with TOCTOU race.

    This test proves that if the directory is created between exists() check
    and mkdir(), then mkdir(exist_ok=False) raises FileExistsError.
    The fix should use exist_ok=True to handle this gracefully.
    """
    target_path = tmp_path / "racedir3" / "file.json"
    parent = target_path.parent

    # Verify parent doesn't exist initially
    assert not parent.exists()

    # Simulate: another thread creates the directory after our check
    parent.mkdir(parents=True)

    # Now the directory exists
    assert parent.exists()

    # Calling mkdir(exist_ok=False) should fail - this is the buggy behavior
    with pytest.raises(FileExistsError):
        parent.mkdir(parents=True, exist_ok=False)

    # But mkdir(exist_ok=True) should succeed - this is the fixed behavior
    parent.mkdir(parents=True, exist_ok=True)  # Should not raise


def test_ensure_parent_directory_toctou_detects_exist_ok_value(
    tmp_path: Path,
) -> None:
    """Verify that _ensure_parent_directory uses exist_ok=True after the fix.

    This test directly verifies that mkdir is called with the correct
    exist_ok parameter by intercepting the call.
    """
    import pathlib

    target_path = tmp_path / "racedir4" / "file.json"
    parent = target_path.parent

    # Store original mkdir method
    original_mkdir = Path.mkdir

    # Track mkdir calls
    mkdir_calls: list[tuple[Path, dict]] = []

    def tracking_mkdir(
        self: Path,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = True,
    ) -> None:
        """Track mkdir calls to verify exist_ok parameter."""
        mkdir_calls.append((self, {"mode": mode, "parents": parents, "exist_ok": exist_ok}))
        return original_mkdir(self, mode=mode, parents=parents, exist_ok=exist_ok)

    # Patch mkdir to track calls
    with patch.object(pathlib.Path, "mkdir", tracking_mkdir):
        _ensure_parent_directory(target_path)

    # Verify mkdir was called with exist_ok=True (the fix)
    # Find the call for our parent directory
    parent_mkdir_calls = [(p, kwargs) for p, kwargs in mkdir_calls if p == parent]
    assert len(parent_mkdir_calls) >= 1, "mkdir should have been called for parent"

    # Check that exist_ok was True (the fix)
    _, kwargs = parent_mkdir_calls[0]
    assert kwargs["exist_ok"] is True, (
        "mkdir should be called with exist_ok=True to handle TOCTOU races. "
        "This is the fix for issue #3923."
    )
