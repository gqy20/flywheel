"""Tests for dirty threshold functionality (Issue #563)."""

import time
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage


def test_dirty_threshold_batches_rapid_writes():
    """Test that rapid small writes are batched based on time threshold."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage with custom MIN_SAVE_INTERVAL for testing
        storage = Storage(str(storage_path))

        # Set a short threshold for testing
        storage.MIN_SAVE_INTERVAL = 0.5  # 500ms threshold

        # Make a change (sets _dirty = True)
        from flywheel.todo import Todo
        todo = Todo("Test task")
        storage.add(todo)
        first_save_time = storage.last_saved_time

        # Immediately make another change (should be batched)
        time.sleep(0.1)  # Wait less than threshold
        todo2 = Todo("Test task 2")
        storage.add(todo2)

        # The last_saved_time should not have updated yet
        # because we're within the threshold
        assert storage.last_saved_time == first_save_time

        # Wait for threshold to pass
        time.sleep(0.6)

        # Trigger cleanup - should save now
        storage._cleanup()

        # Verify the data was saved correctly
        storage2 = Storage(str(storage_path))
        assert len(storage2.list()) == 2


def test_dirty_threshold_respects_time_threshold():
    """Test that writes only occur after MIN_SAVE_INTERVAL has passed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        storage = Storage(str(storage_path))
        storage.MIN_SAVE_INTERVAL = 0.5  # 500ms threshold

        from flywheel.todo import Todo

        # Make first change
        storage.add(Todo("Task 1"))
        first_save_time = storage.last_saved_time

        # Make second change immediately (within threshold)
        time.sleep(0.1)
        storage.add(Todo("Task 2"))

        # Make third change after threshold
        time.sleep(0.6)
        storage.add(Todo("Task 3"))

        # The last_saved_time should have updated for the third change
        assert storage.last_saved_time > first_save_time


def test_cleanup_only_saves_after_threshold():
    """Test that _cleanup only saves if threshold has passed since last save."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        storage = Storage(str(storage_path))
        storage.MIN_SAVE_INTERVAL = 0.5  # 500ms threshold

        from flywheel.todo import Todo

        # Add a todo
        storage.add(Todo("Task 1"))
        initial_save_time = storage.last_saved_time

        # Immediately trigger cleanup (within threshold)
        # This should NOT save because threshold hasn't passed
        time.sleep(0.1)

        # Add another todo to set dirty flag
        storage.add(Todo("Task 2"))

        # Get file modification time before cleanup
        mtime_before = storage_path.stat().st_mtime

        # Trigger cleanup immediately
        storage._cleanup()

        # Get file modification time after cleanup
        mtime_after = storage_path.stat().st_mtime

        # File should not have been modified (within threshold)
        # But this test will FAIL initially because we haven't implemented
        # the threshold logic yet
        assert mtime_after == mtime_before, "File should not be saved within threshold"


def test_forced_save_ignores_threshold():
    """Test that forced saves (like explicit save calls) ignore the threshold."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        storage = Storage(str(storage_path))
        storage.MIN_SAVE_INTERVAL = 0.5

        from flywheel.todo import Todo

        # Add a todo
        storage.add(Todo("Task 1"))
        initial_save_time = storage.last_saved_time

        # Immediately call _save directly (forced save)
        time.sleep(0.1)
        storage._save()

        # This should update last_saved_time regardless of threshold
        assert storage.last_saved_time > initial_save_time
