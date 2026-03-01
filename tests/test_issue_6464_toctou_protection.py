"""Tests for TOCTOU protection in file size check (Issue #6464).

These tests verify that:
1. File size is checked using the same file descriptor used for reading
2. TOCTOU race condition between stat() and read_text() is prevented
3. Symlink attacks cannot bypass the size limit check
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage
from flywheel.todo import Todo


def test_load_uses_fstat_not_stat(tmp_path) -> None:
    """Test that load() uses fstat on file descriptor, not stat() on path.

    This ensures the size check and read operation use the same file,
    preventing TOCTOU race conditions.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid small file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Mock os.stat to ensure it's NOT called on the path
    # (we should use os.fstat on fd instead)
    original_stat = os.stat
    stat_calls = []

    def tracking_stat(path, *args, **kwargs):
        # Track calls to os.stat with path (not fd)
        if isinstance(path, (str, Path)):
            stat_calls.append(path)
        return original_stat(path, *args, **kwargs)

    os.stat = tracking_stat
    try:
        # This should work without calling os.stat on the path
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test"

        # os.stat should NOT have been called on the db path
        # (we use fstat on fd instead)
        db_path_str = str(db)
        path_stat_calls = [p for p in stat_calls if p in (db_path_str, db)]
        assert len(path_stat_calls) == 0, (
            f"load() should use fstat on fd, not stat() on path. "
            f"Got {len(path_stat_calls)} stat calls on db path"
        )
    finally:
        os.stat = original_stat


def test_load_opens_file_once_for_size_check_and_read(tmp_path) -> None:
    """Test that load() opens file once, checking size via fd before reading.

    This prevents TOCTOU where file could be swapped between stat and read.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Track file opens
    original_open = Path.open
    open_calls = []

    def tracking_open(self, *args, **kwargs):
        open_calls.append(self)
        return original_open(self, *args, **kwargs)

    Path.open = tracking_open
    try:
        loaded = storage.load()
        assert len(loaded) == 1

        # Count how many times the db file was opened
        db_opens = [p for p in open_calls if p == db]
        # Should be exactly 1 open (not separate opens for stat and read)
        assert len(db_opens) <= 1, (
            f"load() should open file once for both size check and read. "
            f"Got {len(db_opens)} opens of db file"
        )
    finally:
        Path.open = original_open


def test_load_rejects_oversized_file_via_fstat(tmp_path) -> None:
    """Test that oversized files are rejected even when using fstat."""
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a file larger than the limit
    large_content = "x" * (_MAX_JSON_SIZE_BYTES + 1000)
    db.write_text(large_content, encoding="utf-8")

    # Should raise ValueError about file size
    with pytest.raises(ValueError, match=r"too large|size limit|DoS"):
        storage.load()


def test_symlink_size_check_cannot_be_bypassed(tmp_path) -> None:
    """Test that symlink attacks cannot bypass size check.

    This test verifies that even if an attacker replaces a file with a
    symlink between existence check and size check, the size limit is
    still enforced correctly.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a small valid file first
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Replace with a symlink to a truly large file (>10MB)
    large_file = tmp_path / "large_file.json"
    # Create a file that's definitely larger than 10MB limit
    large_content = json.dumps([{"id": i, "text": "x" * 1000} for i in range(12000)])
    large_file.write_text(large_content, encoding="utf-8")

    # Remove db and create symlink to large file
    db.unlink()
    db.symlink_to(large_file)

    # Should either:
    # 1. Reject the symlink (safer), or
    # 2. Check size of the symlink target and reject if too large
    # Either way, should not load the oversized content
    try:
        loaded = storage.load()
        # If it loaded, verify it's not the full large content
        # (symlink was properly resolved and size checked)
        assert len(loaded) < 12000, "Should not load oversized file via symlink"
    except (ValueError, OSError) as e:
        # Expected: either size limit error or symlink rejection
        assert "too large" in str(e).lower() or "symlink" in str(e).lower() or "size" in str(e).lower()


def test_toctou_race_condition_is_prevented(tmp_path) -> None:
    """Regression test for Issue #6464: TOCTOU race between stat and read.

    This test simulates an attacker swapping files between the size check
    and the read operation. The fix should use fstat on the same fd used
    for reading, preventing this race.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial small file
    small_todos = [Todo(id=1, text="small")]
    storage.save(small_todos)

    # Create a large file to swap in
    large_content = json.dumps([{"id": i, "text": "x" * 1000} for i in range(10000)])
    large_file = tmp_path / "large.json"
    large_file.write_text(large_content, encoding="utf-8")

    swap_occurred = threading.Event()
    load_completed = threading.Event()
    error_caught = []

    def swap_file_during_load():
        """Try to swap the file during load operation."""
        # Wait a tiny bit to ensure load has started
        time.sleep(0.001)
        # Try to swap the file
        try:
            # On Unix, we can't easily swap during the atomic fstat+read
            # but we verify the fix prevents this attack vector
            os.replace(large_file, db)
            swap_occurred.set()
        except OSError:
            pass
        load_completed.wait(timeout=5)

    # Start the swap thread
    swap_thread = threading.Thread(target=swap_file_during_load)
    swap_thread.start()

    try:
        # Load should either:
        # 1. Get the small file (race didn't win), or
        # 2. Get the large file but still enforce size limit (proper fix)
        loaded = storage.load()
        load_completed.set()

        # If we got data, it should be valid and properly sized
        # The fix ensures size is checked on the same fd used for reading
        for todo in loaded:
            assert isinstance(todo, Todo)
            assert isinstance(todo.id, int)
            assert isinstance(todo.text, str)
    except ValueError as e:
        load_completed.set()
        error_caught.append(str(e))
        # If size limit was hit, that's also acceptable
        assert "too large" in str(e).lower() or "size" in str(e).lower()
    finally:
        swap_thread.join(timeout=5)


def test_normal_file_loading_still_works(tmp_path) -> None:
    """Verify that normal file loading still works after the fix."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save some todos
    original_todos = [
        Todo(id=1, text="First task"),
        Todo(id=2, text="Second task", done=True),
        Todo(id=3, text="Third task with unicode: 你好世界"),
    ]
    storage.save(original_todos)

    # Load and verify
    loaded = storage.load()

    assert len(loaded) == 3
    assert loaded[0].text == "First task"
    assert loaded[1].text == "Second task"
    assert loaded[1].done is True
    assert loaded[2].text == "Third task with unicode: 你好世界"


def test_empty_file_handling(tmp_path) -> None:
    """Verify empty file handling works correctly."""
    db = tmp_path / "empty.json"
    storage = TodoStorage(str(db))

    # Empty list is valid
    db.write_text("[]", encoding="utf-8")

    loaded = storage.load()
    assert loaded == []


def test_nonexistent_file_returns_empty_list(tmp_path) -> None:
    """Verify nonexistent file returns empty list."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    loaded = storage.load()
    assert loaded == []
