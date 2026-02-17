"""Regression tests for issue #3923: TOCTOU race condition in _ensure_parent_directory.

Issue: Between the check `if not parent.exists()` and `parent.mkdir(parents=True, exist_ok=False)`,
there's a race window where another thread could create the directory, causing OSError 'File Exists'.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import threading

import pytest

from flywheel.storage import _ensure_parent_directory


def test_concurrent_ensure_parent_directory_no_race_condition(tmp_path) -> None:
    """Issue #3923: Multiple concurrent calls should not raise OSError.

    Before fix: Race condition between exists() check and mkdir(exist_ok=False)
    causes FileExistsError when multiple threads try to create the same directory.

    After fix: Using exist_ok=True handles concurrent directory creation gracefully.
    """
    # Create a path that doesn't exist yet
    shared_path = tmp_path / "shared" / "nested" / "db.json"
    errors: list[Exception] = []
    success_count = 0
    lock = threading.Lock()

    def ensure_directory_worker():
        """Worker that calls _ensure_parent_directory on the same path."""
        nonlocal success_count
        try:
            _ensure_parent_directory(shared_path)
            with lock:
                success_count += 1
        except Exception as e:
            errors.append(e)

    # Run multiple threads concurrently on the same path
    num_threads = 10
    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=ensure_directory_worker)
        threads.append(t)

    # Start all threads as close together as possible
    for t in threads:
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join(timeout=10)

    # No thread should have encountered an error
    assert len(errors) == 0, f"Threads encountered errors: {[str(e) for e in errors]}"

    # All threads should have succeeded
    assert success_count == num_threads, f"Expected {num_threads} successes, got {success_count}"

    # Directory should exist after all threads complete
    assert shared_path.parent.exists(), "Parent directory should exist after concurrent calls"
    assert shared_path.parent.is_dir(), "Parent should be a directory"


def test_concurrent_ensure_parent_directory_with_barrier(tmp_path) -> None:
    """Issue #3923: Use a barrier to maximize race condition likelihood.

    This test uses a threading barrier to ensure all threads reach the
    _ensure_parent_directory call at the same time, maximizing the chance
    of triggering the race condition.
    """
    shared_path = tmp_path / "concurrent" / "deep" / "path" / "db.json"
    num_threads = 8
    barrier = threading.Barrier(num_threads)
    errors: list[Exception] = []
    success_count = 0
    lock = threading.Lock()

    def ensure_directory_worker_with_barrier():
        """Worker that waits at barrier before calling _ensure_parent_directory."""
        nonlocal success_count
        try:
            # Wait for all threads to be ready
            barrier.wait(timeout=10)
            # Now all threads call _ensure_parent_directory at almost the same time
            _ensure_parent_directory(shared_path)
            with lock:
                success_count += 1
        except Exception as e:
            errors.append(e)

    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=ensure_directory_worker_with_barrier)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=10)

    # No thread should have encountered FileExistsError or OSError
    assert len(errors) == 0, f"Threads encountered errors: {[str(e) for e in errors]}"
    assert success_count == num_threads
    assert shared_path.parent.exists()


def test_single_threaded_behavior_unchanged(tmp_path) -> None:
    """Issue #3923: Verify single-threaded behavior remains unchanged.

    The fix should not affect single-threaded usage:
    - Directories are created when needed
    - File-as-directory validation still works correctly
    """
    # Test 1: Directory is created when needed
    new_path = tmp_path / "new" / "path" / "db.json"
    assert not new_path.parent.exists()
    _ensure_parent_directory(new_path)
    assert new_path.parent.exists()
    assert new_path.parent.is_dir()

    # Test 2: Calling again when directory exists should work (idempotent)
    _ensure_parent_directory(new_path)
    assert new_path.parent.exists()

    # Test 3: File-as-directory validation still works
    # Create a file where a directory should be
    blocking_file = tmp_path / "blocking.txt"
    blocking_file.write_text("I am a file")

    # This path would require blocking.txt to be a directory
    invalid_path = blocking_file / "subdir" / "db.json"

    with pytest.raises(ValueError, match=r"(file|not a directory|exists)"):
        _ensure_parent_directory(invalid_path)
