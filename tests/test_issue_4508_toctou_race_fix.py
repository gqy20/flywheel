"""Regression tests for issue #4508: TOCTOU race condition in _ensure_parent_directory.

Issue: The exists() check followed by is_dir() and mkdir() has race windows where:
1. Between part.exists() and part.is_dir() - file type could change
2. Between parent.exists() and parent.mkdir() - directory could be created

Fix: Use atomic mkdir(parents=True, exist_ok=True) with proper FileExistsError handling.

These tests verify that the TOCTOU race conditions are handled atomically.
"""

from __future__ import annotations

import concurrent.futures
import threading

import pytest

from flywheel.storage import _ensure_parent_directory


def test_concurrent_mkdir_no_race_condition(tmp_path) -> None:
    """Issue #4508: Concurrent calls to create same parent directory should not fail.

    Before fix: exists() check followed by mkdir() creates race window where:
    - Thread A checks exists() -> False
    - Thread B checks exists() -> False
    - Thread A creates directory
    - Thread B tries to create directory -> fails with FileExistsError

    After fix: Using mkdir(parents=True, exist_ok=True) handles this atomically.
    """
    # All threads will try to create the same parent directory structure
    db_path = tmp_path / "shared" / "nested" / "todo.json"
    num_threads = 10
    success_count = 0
    lock = threading.Lock()

    def create_parent_dir() -> None:
        nonlocal success_count
        _ensure_parent_directory(db_path)
        with lock:
            success_count += 1

    # Run concurrent directory creation attempts
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(create_parent_dir) for _ in range(num_threads)]
        for future in concurrent.futures.as_completed(futures):
            # All should complete without exception
            future.result()  # Will raise if any thread failed

    # All threads should have succeeded
    assert success_count == num_threads, f"Expected {num_threads} successes, got {success_count}"
    assert db_path.parent.exists()
    assert db_path.parent.is_dir()


def test_toctou_atomic_file_vs_directory_detection(tmp_path) -> None:
    """Issue #4508: Detection of file-as-directory should be atomic after mkdir.

    The fix changes the order: try atomic mkdir first, then check for file conflicts
    after mkdir fails with FileExistsError. This eliminates the race window between
    exists() and is_dir() checks.
    """
    # Create a file where a directory would need to be created
    blocking_file = tmp_path / "blocking"
    blocking_file.write_text("I am a file")

    # Path that requires the file to be a directory
    db_path = blocking_file / "subdir" / "todo.json"

    # Should raise ValueError with clear message about file vs directory conflict
    with pytest.raises(ValueError, match=r"(exists as a file|not a directory)"):
        _ensure_parent_directory(db_path)


def test_toctou_exists_then_mkdir_race_handled(tmp_path) -> None:
    """Issue #4508: Race between exists() and mkdir() should be handled gracefully.

    Simulates the race condition where:
    1. exists() returns False
    2. Another process creates the directory
    3. mkdir() is called and should succeed due to exist_ok=True

    This test verifies the fix uses exist_ok=True to make mkdir atomic.
    """
    db_path = tmp_path / "concurrent" / "todo.json"

    # Create a barrier to synchronize threads
    barrier = threading.Barrier(2)
    mkdir_results = []

    def create_with_barrier() -> None:
        barrier.wait()  # Both threads start at same time
        try:
            _ensure_parent_directory(db_path)
            mkdir_results.append(True)
        except Exception:
            mkdir_results.append(False)

    # Two threads trying to create same directory simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(create_with_barrier) for _ in range(2)]
        for future in concurrent.futures.as_completed(futures):
            future.result()

    # Both should succeed due to atomic mkdir with exist_ok=True
    assert all(mkdir_results), "Both threads should succeed with atomic mkdir"
    assert db_path.parent.is_dir()


def test_nested_toctou_race_handled(tmp_path) -> None:
    """Issue #4508: Nested directory creation with concurrent calls should be safe."""
    # Multiple levels of nesting
    db_path = tmp_path / "a" / "b" / "c" / "d" / "todo.json"
    num_threads = 5
    results = []

    def create_nested() -> None:
        try:
            _ensure_parent_directory(db_path)
            results.append(True)
        except Exception:
            results.append(False)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(create_nested) for _ in range(num_threads)]
        for future in concurrent.futures.as_completed(futures):
            future.result()

    assert all(results), "All threads should succeed with nested atomic mkdir"
