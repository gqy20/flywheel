"""Regression test for issue #4734: TOCTOU race condition in load().

Tests that the load() function handles the race condition where a file
exists during the check but is deleted before the read operation completes.

The fix removes the exists() check and directly attempts to read the file,
handling FileNotFoundError gracefully.
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_handles_file_deleted_after_stat_returns_empty_list(tmp_path) -> None:
    """Regression test for #4734: File deleted between stat() and read_text().

    This simulates the TOCTOU race condition where:
    1. stat() succeeds (file exists at check time)
    2. File is deleted by another process
    3. read_text() would fail with FileNotFoundError

    The fix should handle this gracefully by returning [] (as if file never existed).
    """
    db = tmp_path / "race_test.json"
    storage = TodoStorage(str(db))

    # Create a valid file
    storage.save([Todo(id=1, text="initial")])

    # Verify file exists
    assert db.exists()

    # Simulate the race condition: file exists at stat() time but gets deleted before read_text()
    original_stat = Path.stat
    call_count = [0]

    def race_stat(self, *args, **kwargs):
        """stat() succeeds, but we'll delete the file after."""
        result = original_stat(self, *args, **kwargs)
        call_count[0] += 1
        # First call (the one we care about in load())
        # Delete the file to simulate the race between stat() and read_text()
        if call_count[0] == 1 and self == db and db.exists():
            db.unlink()
        return result

    with patch.object(Path, "stat", race_stat):
        # With the TOCTOU bug, this would raise FileNotFoundError
        # With the fix, it should return [] gracefully
        result = storage.load()

    # Should return empty list (file doesn't exist), not raise FileNotFoundError
    assert result == []


def test_load_nonexistent_file_without_exists_check(tmp_path) -> None:
    """Test that load() handles non-existent file correctly without exists() check.

    The fix removes the explicit exists() check, so this verifies that load()
    correctly handles the FileNotFoundError when file doesn't exist.
    """
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Ensure file doesn't exist
    assert not db.exists()

    # Should return empty list, not raise FileNotFoundError
    result = storage.load()
    assert result == []


def test_load_existing_file_still_works(tmp_path) -> None:
    """Verify that the fix doesn't break normal file loading."""
    db = tmp_path / "existing.json"
    storage = TodoStorage(str(db))

    # Create a file with todos
    todos = [Todo(id=1, text="task one"), Todo(id=2, text="task two", done=True)]
    storage.save(todos)

    # Should load successfully
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "task one"
    assert loaded[1].text == "task two"
    assert loaded[1].done is True


def test_load_concurrent_deletion_returns_empty_list(tmp_path) -> None:
    """Integration test: concurrent file deletion during load returns [].

    This tests the actual race condition with threading to ensure
    the fix handles real-world concurrent scenarios.
    """
    db = tmp_path / "concurrent_race.json"
    storage = TodoStorage(str(db))

    # Create file
    storage.save([Todo(id=1, text="test")])

    results = {"load_result": None, "exception": None}

    def delete_during_load():
        """Thread that deletes file during load operation."""
        import time
        time.sleep(0.001)  # Small delay to let load start
        try:
            if db.exists():
                db.unlink()
        except Exception:
            pass  # File may already be deleted

    def load_operation():
        """Main thread that attempts to load."""
        try:
            results["load_result"] = storage.load()
        except FileNotFoundError as e:
            results["exception"] = e

    # Start delete thread
    delete_thread = threading.Thread(target=delete_during_load)

    # Start both operations
    delete_thread.start()
    load_operation()
    delete_thread.join()

    # Should not raise FileNotFoundError
    assert results["exception"] is None, f"Got FileNotFoundError: {results['exception']}"
    # Result should be [] (if file was deleted) or the original todos
    assert isinstance(results["load_result"], list)
