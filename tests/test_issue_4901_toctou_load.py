"""Regression tests for issue #4901: TOCTOU vulnerability in load().

Issue: Time-of-check to time-of-use (TOCTOU) vulnerability in load() method.
The code checks if a file exists, then later reads the file. Between these
operations, an attacker could replace the file with a symlink pointing to
sensitive files.

Attack scenario:
1. load() checks if path.exists() -> True (regular file exists)
2. Attacker replaces file with symlink to /etc/passwd or other sensitive file
3. load() calls read_text() which follows the symlink and reads sensitive data

The fix: Open the file once and use fstat() on the file descriptor to check
size, preventing any race condition window.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_load_detects_symlink_swap_attack(tmp_path) -> None:
    """Issue #4901: load() should detect or prevent symlink swap attacks.

    Before fix: An attacker can swap a regular file with a symlink between
    the exists() check and read_text() call, causing load() to follow the
    symlink and potentially read sensitive files.

    After fix: The file is opened once, and size is checked via fstat()
    on the same file descriptor. If a symlink swap occurs, the operation
    should fail or detect the inconsistency.

    This test verifies that the fix uses os.open() with O_NOFOLLOW (where
    available) to prevent following symlinks, or detects the symlink via
    fstat() on the opened file descriptor.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Create a sensitive file that attacker wants to read
    # Using a JSON-like structure that could be parsed as valid todo data
    sensitive_file = tmp_path / "sensitive.json"
    sensitive_content = '[{"id": 1, "text": "SECRET_DATA=root:password123", "done": false}]'
    sensitive_file.write_text(sensitive_content)

    # Replace the database with a symlink to sensitive file
    db.unlink()
    db.symlink_to(sensitive_file)

    # The fix should either:
    # 1. Use O_NOFOLLOW and raise OSError (too many levels of symbolic links)
    # 2. Detect symlink via fstat and raise ValueError
    # 3. Otherwise prevent reading symlink content

    # Before fix: load() would follow symlink and read sensitive data
    # After fix: load() should raise an error
    with pytest.raises((OSError, ValueError), match=r"(symlink|symbolic link|Too many levels|invalid|not a regular file)"):
        storage.load()


def test_load_uses_single_file_descriptor(tmp_path) -> None:
    """Issue #4901: load() should use single file descriptor for size check and read.

    Before fix: Code uses path.stat() (separate syscall) and path.read_text()
    (opens file again) - classic TOCTOU window.

    After fix: Code opens file once with open(), uses os.fstat() on the fd,
    and reads from the same file descriptor.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Track fstat calls - the fix should use fstat on the file descriptor
    fstat_calls = []

    original_fstat = os.fstat

    def tracking_fstat(fd):
        result = original_fstat(fd)
        fstat_calls.append(fd)
        return result

    with patch("os.fstat", tracking_fstat):
        result = storage.load()

    # After the fix, fstat should be called on the file descriptor at least once
    # This verifies the code uses fstat instead of path.stat()
    assert len(fstat_calls) >= 1, (
        f"Fix should use os.fstat() on file descriptor for size check, but got {len(fstat_calls)} calls"
    )

    assert len(result) == 1
    assert result[0].text == "test"


def test_load_rejects_symlink_to_large_file(tmp_path) -> None:
    """Issue #4901: load() should reject symlinks even for size checks.

    Even if an attacker manages to create a symlink, the size check should
    use fstat() on the opened file descriptor, which will reveal the symlink.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a large file
    large_file = tmp_path / "large.bin"
    large_content = "x" * (11 * 1024 * 1024)  # 11MB, over the 10MB limit
    large_file.write_text(large_content)

    # Create symlink pointing to large file
    db.unlink(missing_ok=True)
    db.symlink_to(large_file)

    # This should either:
    # 1. Raise ValueError for file too large, OR
    # 2. Raise an error because it's a symlink (if we add O_NOFOLLOW)
    with pytest.raises((ValueError, OSError)):
        storage.load()


def test_load_with_regular_file_still_works(tmp_path) -> None:
    """Issue #4901: load() should still work correctly with regular files."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first todo"),
        Todo(id=2, text="second todo", done=True),
    ]
    storage.save(todos)

    # Should work normally with regular file
    loaded = storage.load()

    assert len(loaded) == 2
    assert loaded[0].text == "first todo"
    assert loaded[1].text == "second todo"
    assert loaded[1].done is True


def test_load_with_nonexistent_file_returns_empty(tmp_path) -> None:
    """Issue #4901: load() should return empty list for nonexistent file."""
    db = tmp_path / "nonexistent.json"
    storage = TodoStorage(str(db))

    result = storage.load()
    assert result == []


def test_load_detects_toctou_via_fstat_consistency(tmp_path) -> None:
    """Issue #4901: load() should detect if file changes between open and read.

    After the fix, the code should open the file once and use fstat() on the
    file descriptor. If the file is swapped between open and read, the
    inode/device info from fstat should be used to validate consistency.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="original")]
    storage.save(todos)

    # Get original file stats
    original_stat = db.stat()
    original_ino = original_stat.st_ino

    # Track stat calls during load
    stat_results = []

    original_fstat = os.fstat

    def tracking_fstat(fd):
        result = original_fstat(fd)
        stat_results.append(result)
        return result

    with patch("os.fstat", tracking_fstat):
        result = storage.load()

    # The fix should use fstat on the file descriptor at least once
    # for the size check
    assert len(stat_results) >= 1, (
        "Fix should use os.fstat() on file descriptor for size check"
    )

    # All fstat calls should be on the same file (same inode)
    if len(stat_results) > 1:
        inodes = [s.st_ino for s in stat_results]
        assert all(i == original_ino for i in inodes), (
            f"fstat should always check same file, but got inodes: {inodes}"
        )

    assert len(result) == 1
    assert result[0].text == "original"
