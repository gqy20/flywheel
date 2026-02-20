"""Tests for fsync behavior in TodoStorage.save().

This test suite verifies that TodoStorage.save() calls fsync to ensure
data is persisted to disk before atomic rename, preventing data loss
in case of system crash or power failure.

Issue: #4613
"""

from __future__ import annotations

import os
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_calls_fsync_by_default(tmp_path) -> None:
    """Test that save() calls fsync on the file descriptor by default."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Track fsync calls
    fsync_called = []
    original_fsync = os.fsync

    def tracking_fsync(fd):
        fsync_called.append(fd)
        return original_fsync(fd)

    with patch("os.fsync", tracking_fsync):
        storage.save(todos)

    # Verify fsync was called
    assert len(fsync_called) == 1, "fsync should be called once during save()"


def test_save_sync_false_skips_fsync(tmp_path) -> None:
    """Test that save(sync=False) does not call fsync."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Track fsync calls
    fsync_called = []

    def mock_fsync(fd):
        fsync_called.append(fd)
        # Don't actually call fsync in test

    with patch("os.fsync", mock_fsync):
        storage.save(todos, sync=False)

    # Verify fsync was NOT called when sync=False
    assert len(fsync_called) == 0, "fsync should not be called when sync=False"


def test_save_sync_true_calls_fsync(tmp_path) -> None:
    """Test that save(sync=True) explicitly calls fsync."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Track fsync calls
    fsync_called = []
    original_fsync = os.fsync

    def tracking_fsync(fd):
        fsync_called.append(fd)
        return original_fsync(fd)

    with patch("os.fsync", tracking_fsync):
        storage.save(todos, sync=True)

    # Verify fsync was called
    assert len(fsync_called) == 1, "fsync should be called when sync=True"


def test_fsync_called_before_replace(tmp_path) -> None:
    """Test that fsync is called before os.replace for proper ordering."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Track call order
    call_order = []

    original_fsync = os.fsync
    original_replace = os.replace

    def tracking_fsync(fd):
        call_order.append(("fsync", fd))
        return original_fsync(fd)

    def tracking_replace(src, dst):
        call_order.append(("replace", src, dst))
        return original_replace(src, dst)

    with patch("os.fsync", tracking_fsync), \
         patch("flywheel.storage.os.replace", tracking_replace):
        storage.save(todos)

    # Verify ordering: fsync should come before replace
    assert len(call_order) == 2, f"Expected 2 calls, got {len(call_order)}"
    assert call_order[0][0] == "fsync", "fsync should be called first"
    assert call_order[1][0] == "replace", "replace should be called after fsync"


def test_save_with_fsync_produces_valid_json(tmp_path) -> None:
    """Test that save with fsync still produces valid JSON."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="task 1"),
        Todo(id=2, text="task 2", done=True),
    ]

    # Save with fsync (default)
    storage.save(todos)

    # Verify file is valid and loadable
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "task 1"
    assert loaded[1].text == "task 2"
    assert loaded[1].done is True
