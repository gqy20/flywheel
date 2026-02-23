"""Regression tests for issue #5432: TOCTOU race condition in _ensure_parent_directory.

Issue: The _ensure_parent_directory function has a time-of-check-to-time-of-use race
between checking if parent.exists() and calling mkdir(exist_ok=False). If another
process creates the directory between these operations, a FileExistsError is raised.

Fix: Use exist_ok=True since the validation (checking no parent is a file) was already
done in the loop above.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _ensure_parent_directory
from flywheel.todo import Todo


def test_ensure_parent_directory_no_race_when_concurrent_creation(tmp_path) -> None:
    """Issue #5432: _ensure_parent_directory should not fail when directory is created concurrently.

    This test simulates a TOCTOU race condition where:
    1. Thread A checks parent.exists() -> False
    2. Thread B creates the directory
    3. Thread A calls mkdir(exist_ok=False) -> FileExistsError (BUG!)

    With the fix, mkdir should use exist_ok=True, so Thread A succeeds.
    """
    db_path = tmp_path / "newdir" / "subdir" / "todo.json"
    parent = db_path.parent

    # Track whether mkdir was called
    mkdir_call_count = 0
    original_mkdir = Path.mkdir

    def racing_mkdir(self, *args, **kwargs):
        nonlocal mkdir_call_count
        mkdir_call_count += 1

        # On first call, simulate another process creating the directory
        # right before our mkdir call (after the exists() check)
        if mkdir_call_count == 1 and not self.exists():
            # Simulate race: another process creates the directory
            original_mkdir(self, parents=True, exist_ok=True)

        # Now call the actual mkdir with whatever exist_ok was passed
        return original_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", racing_mkdir):
        # This should NOT raise FileExistsError
        # Before fix: raises FileExistsError because exist_ok=False but dir exists
        # After fix: succeeds because exist_ok=True
        _ensure_parent_directory(db_path)

    # Verify directory was created
    assert parent.exists()
    assert parent.is_dir()


def test_save_no_race_when_concurrent_mkdir(tmp_path) -> None:
    """Issue #5432: TodoStorage.save() should not fail on concurrent parent directory creation."""
    db_path = tmp_path / "concurrent" / "nested" / "todo.json"
    storage = TodoStorage(str(db_path))

    # Track calls
    original_mkdir = Path.mkdir
    call_count = 0

    def racing_mkdir(self, *args, **kwargs):
        nonlocal call_count
        call_count += 1

        # Simulate race on first mkdir
        if call_count == 1 and not self.exists():
            original_mkdir(self, parents=True, exist_ok=True)

        return original_mkdir(self, *args, **kwargs)

    todos = [Todo(id=1, text="test")]

    with patch.object(Path, "mkdir", racing_mkdir):
        # This should succeed without FileExistsError
        storage.save(todos)

    # Verify data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_multiple_threads_concurrent_save_new_directory(tmp_path) -> None:
    """Issue #5432: Multiple threads saving to same new path should not race on mkdir."""
    db_path = tmp_path / "threaded" / "shared" / "todo.json"

    errors = []

    def save_thread(thread_id: int):
        try:
            storage = TodoStorage(str(db_path))
            todos = [Todo(id=thread_id, text=f"thread-{thread_id}")]
            storage.save(todos)
        except Exception as e:
            errors.append((thread_id, e))

    # Create multiple threads trying to save simultaneously
    threads = [threading.Thread(target=save_thread, args=(i,)) for i in range(5)]

    # Start all threads nearly simultaneously
    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=5)

    # No thread should have encountered FileExistsError
    for thread_id, error in errors:
        assert not isinstance(error, FileExistsError), (
            f"Thread {thread_id} got FileExistsError - race condition detected: {error}"
        )

    # Verify file is valid
    storage = TodoStorage(str(db_path))
    loaded = storage.load()
    assert isinstance(loaded, list)


def test_file_as_parent_still_raises_valueerror(tmp_path) -> None:
    """Issue #5432: After fix, ValueError should still be raised if parent is a file."""
    # Create a file where a directory would be needed
    blocking_file = tmp_path / "blocking_file.json"
    blocking_file.write_text("I am a file")

    # This path requires blocking_file to be a directory
    db_path = blocking_file / "subdir" / "todo.json"

    # Should still raise ValueError (not FileExistsError)
    with pytest.raises(ValueError, match=r"(exists as a file|not a directory)"):
        _ensure_parent_directory(db_path)
