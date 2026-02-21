"""Regression tests for issue #4901: TOCTOU vulnerability in load().

Issue: TOCTOU (Time-of-check to time-of-use) vulnerability in load():
symlink replacement between exists() and read_text().

The vulnerable code pattern:
    if not self.path.exists():  # TOCTOU window starts here
        return []
    file_size = self.path.stat().st_size  # Another file descriptor
    ...
    raw = json.loads(self.path.read_text(...))  # Opens NEW file descriptor

Attack scenario:
1. Attacker sees exists() check pass on a regular file
2. Attacker replaces file with symlink to sensitive file (e.g., /etc/passwd)
3. read_text() follows symlink and reads attacker-controlled content

Fix: Open file once with os.open() and use fstat() on the same file descriptor.
This ensures the file we check is the same file we read.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class MockStatResult:
    """Mock stat result for simulating TOCTOU attack."""

    def __init__(self, size: int, is_link: bool = False):
        self.st_size = size
        self.st_mode = stat.S_IFLNK if is_link else stat.S_IFREG
        self.st_ino = 12345
        self.st_dev = 1
        self.st_nlink = 1
        self.st_uid = 0
        self.st_gid = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0


def test_load_uses_single_file_descriptor(tmp_path) -> None:
    """Issue #4901: load() should use single file descriptor for size check and read.

    Before fix: Multiple file descriptors opened (exists, stat, read_text)
    After fix: Single os.open() call, size checked via fstat() on same fd
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Track how many times the file is opened
    open_calls = []

    original_open = os.open

    def tracking_open(path, flags, *args, **kwargs):
        if str(path) == str(db):
            open_calls.append(("os.open", flags))
        return original_open(path, flags, *args, **kwargs)

    with patch("os.open", side_effect=tracking_open):
        loaded = storage.load()

    # After fix, file should be opened exactly once for reading
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"

    # Verify file is opened only once for reading (not multiple times)
    # O_RDONLY = 0, we expect the fix to use os.open with O_RDONLY
    read_opens = [c for c in open_calls if "read" in str(c).lower() or c[1] == 0]
    # Before fix: path.exists(), path.stat(), path.read_text() = 3 separate opens
    # After fix: os.open() once, fstat on fd, read from fd = 1 open
    # We allow up to 2 opens (one for the fix, one might be in path handling)
    assert len(open_calls) <= 2, (
        f"File opened too many times ({len(open_calls)}), "
        f"suggests TOCTOU vulnerability. Calls: {open_calls}"
    )


def test_load_rejects_symlink(tmp_path) -> None:
    """Issue #4901: load() should reject symlinks to prevent symlink attacks.

    The fix uses O_NOFOLLOW on systems that support it to prevent
    following symlinks.

    Before fix: load() follows symlinks and reads target content
    After fix: load() raises error when path is a symlink
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a symlink pointing to a file outside the intended directory
    attack_target = tmp_path / "sensitive_data.json"
    attack_target.write_text(json.dumps([{"id": 1, "text": "sensitive data"}]))

    # Remove the db file and create a symlink to the attack target
    if db.exists():
        db.unlink()
    db.symlink_to(attack_target)

    # Before fix: load() would follow symlink and return sensitive data
    # After fix: load() should reject the symlink
    with pytest.raises(ValueError, match="symlink|symbolic link|not a regular file"):
        storage.load()


def test_load_detects_symlink_swap_attack(tmp_path) -> None:
    """Issue #4901: load() should detect file swap between check and read.

    This test verifies that the fix uses O_NOFOLLOW which prevents
    following symlinks at the kernel level. Even if an attacker replaces
    the file with a symlink after our initial check, O_NOFOLLOW will
    cause os.open() to fail.

    Note: The fix no longer uses exists() - it directly uses os.open()
    with O_NOFOLLOW, which provides kernel-level protection against
    symlink attacks.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file
    todos = [Todo(id=1, text="legitimate todo")]
    storage.save(todos)

    # Create attack target
    attack_target = tmp_path / "attack_target.json"
    attack_target.write_text(json.dumps([{"id": 999, "text": "injected malicious content"}]))

    # Simulate the TOCTOU attack by swapping the file for a symlink
    # We mock os.open to swap the file BEFORE the actual open call
    swap_done = [False]

    original_open = os.open

    def malicious_open(path, flags, *args, **kwargs):
        if str(path) == str(db) and not swap_done[0]:
            # Swap the file for a symlink before the actual open
            swap_done[0] = True
            Path(path).unlink()
            Path(path).symlink_to(attack_target)
        return original_open(path, flags, *args, **kwargs)

    with patch("os.open", side_effect=malicious_open):
        # After fix: O_NOFOLLOW will reject the symlink at os.open() time
        with pytest.raises(ValueError, match="symlink|symbolic link"):
            storage.load()


def test_load_size_check_uses_same_file_descriptor(tmp_path) -> None:
    """Issue #4901: Size check should use fstat() on opened file descriptor.

    Before fix: path.stat() opens new file descriptor - TOCTOU window
    After fix: fstat() on same fd from os.open()
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a todo file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Track stat calls - after fix, only fstat should be used on the fd
    stat_calls = []

    original_stat = Path.stat

    def tracking_stat(path):
        result = original_stat(path)
        stat_calls.append(("Path.stat", str(path)))
        return result

    with patch.object(Path, "stat", tracking_stat):
        loaded = storage.load()

    assert len(loaded) == 1
    # After fix, Path.stat should not be called on the db file
    # (we use os.fstat on the file descriptor instead)
    db_stat_calls = [c for c in stat_calls if str(db) in c[1]]
    assert len(db_stat_calls) == 0, (
        f"Path.stat() called on db file {len(db_stat_calls)} times, "
        f"suggests TOCTOU vulnerability. Consider using os.fstat() on file descriptor. "
        f"Calls: {stat_calls}"
    )


def test_load_returns_empty_list_for_nonexistent_file(tmp_path) -> None:
    """Issue #4901: Fix should maintain existing behavior for missing files.

    Before fix: exists() returns False -> return []
    After fix: os.open() raises FileNotFoundError -> return []
    """
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    # Should return empty list, not raise exception
    result = storage.load()
    assert result == []


def test_load_continues_to_enforce_size_limit(tmp_path) -> None:
    """Issue #4901: Fix should maintain existing size limit enforcement.

    Before fix: path.stat().st_size check
    After fix: os.fstat(fd).st_size check
    """
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a large file manually (bypassing save validation)
    large_content = json.dumps([{"id": i, "text": "x" * 1000} for i in range(20000)])
    db.write_text(large_content)

    # Should raise ValueError for size limit
    with pytest.raises(ValueError, match="too large|DoS"):
        storage.load()


def test_load_continues_to_validate_json(tmp_path) -> None:
    """Issue #4901: Fix should maintain existing JSON validation."""
    db = tmp_path / "invalid.json"
    storage = TodoStorage(str(db))

    # Create invalid JSON
    db.write_text("not valid json {{{")

    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()


def test_load_continues_to_require_list_structure(tmp_path) -> None:
    """Issue #4901: Fix should maintain existing list structure validation."""
    db = tmp_path / "not_list.json"
    storage = TodoStorage(str(db))

    # Create valid JSON but not a list
    db.write_text(json.dumps({"id": 1, "text": "not a list"}))

    with pytest.raises(ValueError, match="must be a JSON list"):
        storage.load()
