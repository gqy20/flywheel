"""Regression test for issue #2455: TOCTOU race condition in load method.

This test suite verifies that TodoStorage.load() handles file deletion
gracefully between the exists() check and stat()/read_text() calls.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_handles_file_deleted_after_exists_check(tmp_path) -> None:
    """Test that load handles file being deleted between exists() and stat().

    This is a TOCTOU (Time-of-Check to Time-of-Use) vulnerability where:
    1. exists() check passes (line 60)
    2. File is deleted by another process
    3. stat() call fails with FileNotFoundError (line 64)

    The function should return empty list gracefully instead of crashing.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Simulate file being deleted after exists() but before stat()
    original_exists = Path.exists
    call_count = {"exists": 0, "stat": 0}

    def mock_exists(self):
        call_count["exists"] += 1
        result = original_exists(self)
        # After first exists() returns True, simulate file deletion
        if call_count["exists"] == 1 and result:
            # File will be "deleted" before stat() is called
            pass
        return result

    original_stat = Path.stat

    def mock_stat(self, follow_symlinks=True):
        call_count["stat"] += 1
        # Simulate file deleted between exists() and stat()
        if call_count["stat"] >= 1:
            raise FileNotFoundError(f"[Errno 2] No such file or directory: '{self}'")
        return original_stat(self, follow_symlinks=follow_symlinks)

    with (
        patch.object(Path, "exists", mock_exists),
        patch.object(Path, "stat", mock_stat),
    ):
        # Should return empty list gracefully, not raise FileNotFoundError
        result = storage.load()
        assert result == []


def test_load_handles_file_deleted_between_stat_and_read_text(tmp_path) -> None:
    """Test that load handles file being deleted between stat() and read_text().

    This tests the second TOCTOU race window:
    1. exists() check passes (line 60)
    2. stat() call succeeds (line 64)
    3. File is deleted by another process
    4. read_text() call fails with FileNotFoundError (line 74)
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    call_count = {"read_text": 0}

    original_read_text = Path.read_text

    def mock_read_text(self, *args, **kwargs):
        call_count["read_text"] += 1
        # Simulate file deleted between stat() and read_text()
        if call_count["read_text"] >= 1:
            raise FileNotFoundError(f"[Errno 2] No such file or directory: '{self}'")
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", mock_read_text):
        # Should return empty list gracefully, not raise FileNotFoundError
        result = storage.load()
        assert result == []


def test_load_returns_empty_list_when_file_does_not_exist(tmp_path) -> None:
    """Test that load returns empty list when file doesn't exist.

    This is the expected behavior and should continue to work after the fix.
    """
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    result = storage.load()
    assert result == []


def test_load_works_normally_when_file_exists(tmp_path) -> None:
    """Test that load works normally when file exists and is readable.

    This verifies the fix doesn't break normal operation.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first task"),
        Todo(id=2, text="second task", done=True),
    ]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first task"
    assert loaded[1].text == "second task"
    assert loaded[1].done is True


def test_load_concurrent_deletion_scenario(tmp_path) -> None:
    """Test concurrent file deletion scenario with actual file operations.

    This simulates a more realistic race condition where another thread
    deletes the file during load() execution.
    """
    import threading

    db = tmp_path / "race.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Flag to coordinate timing
    ready_to_delete = threading.Event()
    deleted = threading.Event()

    def delete_file_after_delay():
        """Wait for exists() to pass, then delete file."""
        ready_to_delete.wait(timeout=5)
        if db.exists():
            db.unlink()
        deleted.set()

    # Start deletion thread
    deleter = threading.Thread(target=delete_file_after_delay, daemon=True)
    deleter.start()

    # Patch exists() to trigger deletion after it returns
    original_exists = Path.exists

    def trigger_deletion_exists(self):
        result = original_exists(self)
        if result and not ready_to_delete.is_set():
            ready_to_delete.set()
        return result

    # Try to load while file is being deleted
    with patch.object(Path, "exists", trigger_deletion_exists):
        result = storage.load()
        # Should either return data (if read before deletion) or empty list (if deleted)
        # But should never crash
        assert isinstance(result, list)

    deleter.join(timeout=5)
