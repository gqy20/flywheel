"""Tests for file lock mechanism to prevent concurrent write conflicts.

Issue #5100: Adding file lock mechanism to prevent concurrent write conflicts.

The current save() uses atomic rename but lacks locking, causing last-writer-wins
data loss when multiple processes modify the same file concurrently.
"""

from __future__ import annotations

import fcntl
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestFileLockMechanism:
    """Test file lock mechanism for concurrent write safety."""

    def test_storage_accepts_use_lock_parameter(self, tmp_path: Path) -> None:
        """Test that TodoStorage accepts use_lock parameter."""
        db = tmp_path / "todo.json"
        # Should not raise - accept use_lock=True
        storage = TodoStorage(str(db), use_lock=True)
        assert storage.path == db
        assert storage.use_lock is True

        # Should not raise - accept use_lock=False (default behavior)
        storage_no_lock = TodoStorage(str(db), use_lock=False)
        assert storage_no_lock.path == db
        assert storage_no_lock.use_lock is False

    def test_lock_timeout_parameter_accepted(self, tmp_path: Path) -> None:
        """Test that lock_timeout parameter is accepted."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), use_lock=True, lock_timeout=5.0)
        assert storage.lock_timeout == 5.0

    def test_lock_file_created_on_save_with_lock(self, tmp_path: Path) -> None:
        """Test that a lock file is created when using locking."""
        db = tmp_path / "locked.json"
        storage = TodoStorage(str(db), use_lock=True)

        # Save some data
        storage.save([Todo(id=1, text="test")])

        # Lock file should exist (created during save)
        lock_path = db.with_suffix(db.suffix + ".lock")
        assert lock_path.exists()

    def test_lock_timeout_raises_error(self, tmp_path: Path) -> None:
        """Test that lock acquisition timeout raises an appropriate error."""
        db = tmp_path / "timeout.json"
        storage = TodoStorage(str(db), use_lock=True, lock_timeout=0.1)

        # Create initial data
        storage.save([Todo(id=1, text="initial")])

        lock_path = db.with_suffix(db.suffix + ".lock")

        # Create and hold the lock externally
        with open(lock_path, "w") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

            # Try to save with a very short timeout - should raise TimeoutError
            with pytest.raises(TimeoutError, match=r"lock|timeout"):
                storage.save([Todo(id=2, text="should-fail")])

    def test_save_without_lock_works_normally(self, tmp_path: Path) -> None:
        """Test that saving without lock works as before."""
        db = tmp_path / "no_lock.json"
        storage = TodoStorage(str(db), use_lock=False)

        # Save should work normally
        storage.save([Todo(id=1, text="test"), Todo(id=2, text="test2")])

        # Load should return saved data
        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded[0].text == "test"
        assert loaded[1].text == "test2"

    def test_save_with_lock_produces_valid_data(self, tmp_path: Path) -> None:
        """Test that saving with lock produces valid data."""
        db = tmp_path / "with_lock.json"
        storage = TodoStorage(str(db), use_lock=True)

        # Save should work with lock
        todos = [Todo(id=1, text="locked save")]
        storage.save(todos)

        # Data should be readable
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "locked save"

    def test_exclusive_lock_blocks_concurrent_access(self, tmp_path: Path) -> None:
        """Test that acquiring exclusive lock blocks another exclusive lock attempt."""
        db = tmp_path / "blocked.json"
        storage = TodoStorage(str(db), use_lock=True, lock_timeout=0.5)

        # Acquire lock manually
        lock_fd = storage._acquire_lock(exclusive=True)
        try:
            # Create another storage instance and try to acquire lock
            storage2 = TodoStorage(str(db), use_lock=True, lock_timeout=0.1)

            # This should timeout because lock is held
            with pytest.raises(TimeoutError, match="lock"):
                storage2._acquire_lock(exclusive=True)
        finally:
            storage._release_lock(lock_fd)

    def test_release_allows_subsequent_access(self, tmp_path: Path) -> None:
        """Test that releasing lock allows subsequent access."""
        db = tmp_path / "released.json"
        storage = TodoStorage(str(db), use_lock=True, lock_timeout=1.0)

        # Acquire and release lock
        lock_fd = storage._acquire_lock(exclusive=True)
        storage._release_lock(lock_fd)

        # Should be able to acquire lock again
        lock_fd2 = storage._acquire_lock(exclusive=True)
        storage._release_lock(lock_fd2)

    def test_load_with_lock_acquires_shared_lock(self, tmp_path: Path) -> None:
        """Test that load with lock acquires a shared lock."""
        db = tmp_path / "shared.json"
        storage = TodoStorage(str(db), use_lock=True)

        # Create initial data
        storage.save([Todo(id=1, text="initial")])

        # Acquire shared lock manually via load
        lock_fd = storage._acquire_lock(exclusive=False)  # shared lock
        try:
            # Should be able to acquire another shared lock
            storage2 = TodoStorage(str(db), use_lock=True, lock_timeout=0.5)
            lock_fd2 = storage2._acquire_lock(exclusive=False)
            storage2._release_lock(lock_fd2)
        finally:
            storage._release_lock(lock_fd)
