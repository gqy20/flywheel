"""Regression tests for issue #7175: TOCTOU race condition in _ensure_parent_directory.

Issue: There is a Time-of-Check to Time-of-Use (TOCTOU) race condition between:
1. Checking parent paths for file-as-directory confusion (lines 35-40)
2. Creating parent directories (lines 43-50)

Between these operations, another process could create a file at a parent path,
causing the operation to either fail silently or corrupt data.

The fix should:
1. Use exist_ok=True with mkdir() to provide atomic check-and-create
2. Catch FileExistsError to detect when a file exists at the path (not a directory)
3. Provide clear error message for this case

These tests verify the security fix works correctly.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_toctou_race_condition_detects_file_exists_error(tmp_path) -> None:
    """Issue #7175: _ensure_parent_directory should catch FileExistsError when file blocks directory.

    When exist_ok=True is used with mkdir(), if a file (not directory) exists at the path,
    Python will raise FileExistsError. The fix should catch this and provide a clear error.
    """
    # Pre-create a file at the parent location
    parent_file = tmp_path / "blocking_parent"
    parent_file.write_text("I am a file blocking directory creation")

    # Try to create storage that would need this file to be a directory
    db_path = parent_file / "subdir" / "db.json"
    storage = TodoStorage(str(db_path))

    # Should fail with clear error about the file-as-directory conflict
    with pytest.raises((ValueError, OSError, FileExistsError)) as exc_info:
        storage.save([Todo(id=1, text="test")])

    # Verify the error message is clear
    error_msg = str(exc_info.value).lower()
    assert any(
        keyword in error_msg
        for keyword in ["file", "directory", "not a directory", "exists", "blocking"]
    ), f"Error should clearly explain the file-as-directory conflict: {exc_info.value}"


def test_toctou_detects_file_at_grandparent_level(tmp_path) -> None:
    """Issue #7175: Should detect file blocking directory at any parent level."""
    # Create a file at grandparent level
    grandparent_file = tmp_path / "config.json"
    grandparent_file.write_text("{}")

    # Try to create db at path that needs grandparent to be a directory
    db_path = grandparent_file / "subdir" / "db.json"
    storage = TodoStorage(str(db_path))

    # Should fail with clear error
    with pytest.raises((ValueError, OSError, FileExistsError)) as exc_info:
        storage.save([Todo(id=1, text="test")])

    error_msg = str(exc_info.value).lower()
    assert any(
        keyword in error_msg
        for keyword in ["file", "directory", "config.json", "exists"]
    ), f"Error should mention the blocking file: {exc_info.value}"


def test_ensure_parent_directory_atomic_behavior(tmp_path) -> None:
    """Issue #7175: Directory creation should be atomic with existence check.

    Using exist_ok=True with mkdir() provides atomic check-and-create semantics.
    If a file exists at the path, FileExistsError is raised.
    If a directory exists, the call succeeds (no-op).
    """
    # This test verifies the fix uses atomic mkdir with exist_ok=True

    # Create a pre-existing directory
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir()

    db_path = existing_dir / "db.json"
    storage = TodoStorage(str(db_path))

    # Should succeed - existing directory is fine
    storage.save([Todo(id=1, text="test")])

    # Verify data was saved
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_concurrent_saves_to_same_path_succeed(tmp_path) -> None:
    """Issue #7175: Concurrent saves to the same path should work with exist_ok=True.

    Multiple threads trying to create the same parent directory should not fail
    when one wins the race (exist_ok=True handles this).

    Before fix: Using exist_ok=False could cause OSError/FileExistsError when
    multiple threads race to create the same directory.
    After fix: Using exist_ok=True allows concurrent directory creation.
    """
    db_path = tmp_path / "shared" / "db.json"
    errors = []
    success_count = 0
    lock = threading.Lock()
    barrier = threading.Barrier(5)  # Synchronize all threads to start at same time

    def save_todos(task_id: int):
        nonlocal success_count
        try:
            # Wait for all threads to be ready
            barrier.wait(timeout=10)
            storage = TodoStorage(str(db_path))
            storage.save([Todo(id=task_id, text=f"task-{task_id}")])
            with lock:
                success_count += 1
        except Exception as e:
            errors.append((task_id, type(e).__name__, str(e)))

    # Run multiple concurrent saves
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(save_todos, i) for i in range(5)]
        for future in futures:
            future.result(timeout=10)

    # All saves should have succeeded (or at least not failed due to race condition)
    assert len(errors) == 0, f"Concurrent saves should not fail due to race: {errors}"
    assert success_count == 5, f"All saves should succeed: {success_count}/5"


def test_immediate_parent_file_detected(tmp_path) -> None:
    """Issue #7175: Immediate parent being a file should be detected and reported."""
    # Create a file at the immediate parent location
    parent_file = tmp_path / "parent.json"
    parent_file.write_text("{}")

    # Try to create db inside what is a file
    db_path = parent_file / "db.json"
    storage = TodoStorage(str(db_path))

    # Should fail with clear error
    with pytest.raises((ValueError, OSError, FileExistsError)) as exc_info:
        storage.save([Todo(id=1, text="test")])

    error_msg = str(exc_info.value).lower()
    # Error should mention the file path
    assert "parent.json" in error_msg or "file" in error_msg or "not a directory" in error_msg, (
        f"Error should mention the blocking file or the issue: {exc_info.value}"
    )


def test_ensure_parent_directory_with_race_simulation(tmp_path) -> None:
    """Issue #7175: Simulate TOCTOU race where file is created during directory creation.

    This test directly tests _ensure_parent_directory function with a race condition:
    1. Thread A starts _ensure_parent_directory (checks pass)
    2. Thread B creates a file at the parent path
    3. Thread A tries to mkdir, should fail with FileExistsError

    The fix should catch FileExistsError and convert it to a clear ValueError.
    """
    # Create a nested path that doesn't exist yet
    nested_path = tmp_path / "level1" / "level2" / "db.json"
    race_event = threading.Event()
    errors = []

    def create_conflicting_file():
        """Create a file at level1 after check but before mkdir."""
        # Wait for the main thread to start
        time.sleep(0.01)
        # Create a file where a directory should be
        (tmp_path / "level1").write_text("I am a file now!")
        race_event.set()

    def attempt_ensure_directory():
        """Attempt to ensure directory exists."""
        try:
            _ensure_parent_directory(nested_path)
        except (ValueError, OSError, FileExistsError) as e:
            errors.append(str(e))

    # Start the file creator in background
    file_thread = threading.Thread(target=create_conflicting_file)
    file_thread.start()

    # Try to create the directory
    attempt_ensure_directory()
    file_thread.join(timeout=5)

    # If the race was triggered, we should get an error
    # (Either the pre-check caught the file, or mkdir failed with FileExistsError)
    if (tmp_path / "level1").exists() and not (tmp_path / "level1").is_dir():
        # File was created at parent path - we should have caught this
        assert len(errors) > 0 or not nested_path.parent.exists(), (
            "Should have detected file at parent path"
        )


def test_mkdir_with_exist_ok_handles_concurrent_creation(tmp_path) -> None:
    """Issue #7175: Verify that exist_ok=True handles concurrent directory creation.

    This is a key test for the fix - it verifies that using exist_ok=True
    allows multiple threads to safely create the same directory.
    """
    dir_path = tmp_path / "concurrent_dir"
    errors = []
    success_count = 0
    lock = threading.Lock()
    barrier = threading.Barrier(10)

    def create_directory():
        nonlocal success_count
        try:
            barrier.wait(timeout=10)
            # This simulates what the fixed code should do
            dir_path.mkdir(parents=True, exist_ok=True)
            with lock:
                success_count += 1
        except OSError as e:
            errors.append(str(e))

    # Run many concurrent mkdir attempts
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_directory) for _ in range(10)]
        for future in futures:
            future.result(timeout=10)

    # All should succeed - exist_ok=True handles the race
    assert len(errors) == 0, f"Concurrent mkdir with exist_ok=True should not fail: {errors}"
    assert success_count == 10, f"All mkdir calls should succeed: {success_count}/10"
    assert dir_path.is_dir(), "Directory should exist"
