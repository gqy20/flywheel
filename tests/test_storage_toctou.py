"""Tests for TOCTOU vulnerability prevention in TodoStorage.load().

This test suite verifies that TodoStorage.load() is resistant to
Time-of-Check-Time-of-Use (TOCTOU) symlink attacks where an attacker
replaces the file with a symlink between the exists() check and read_text().
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage


def test_load_rejects_symlink_directly(tmp_path) -> None:
    """Test that load() rejects symlinks entirely.

    This is the key regression test for the TOCTOU vulnerability.
    The fix uses os.open() with O_NOFOLLOW to reject symlinks.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a target file with JSON content
    target = tmp_path / "target.json"
    target.write_text('[{"id": 1, "text": "target content", "done": false}]', encoding="utf-8")

    # Create a symlink pointing to the target
    db.symlink_to(target)

    # The fixed code should reject symlinks for security
    with pytest.raises(ValueError, match=r"symlink|cannot follow|symbolic"):
        storage.load()


def test_load_normal_file_still_works(tmp_path) -> None:
    """Test that normal file loading still works after the TOCTOU fix."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    db.write_text('[{"id": 1, "text": "normal todo", "done": false}]', encoding="utf-8")

    # Should load successfully
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].id == 1
    assert todos[0].text == "normal todo"
    assert todos[0].done is False


def test_load_empty_file_returns_empty_list(tmp_path) -> None:
    """Test that a non-existent file returns an empty list."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # File doesn't exist, should return empty list
    todos = storage.load()
    assert todos == []


def test_load_size_check_uses_fstat_not_path_stat(tmp_path) -> None:
    """Test that size check uses fstat() on file descriptor, not stat() on path.

    This verifies that after opening the file, we check size using the fd
    to prevent TOCTOU where the file could change between open and stat.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    db.write_text('[{"id": 1, "text": "valid", "done": false}]', encoding="utf-8")

    # Track if os.fstat is called (the secure approach)
    fstat_calls = []
    original_fstat = os.fstat

    def tracking_fstat(fd):
        fstat_calls.append(fd)
        return original_fstat(fd)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(os, "fstat", tracking_fstat)
        storage.load()

    # The fixed code should use fstat on the file descriptor
    assert len(fstat_calls) >= 1, (
        "load() should use os.fstat() on file descriptor for size check, "
        "not Path.stat() which is vulnerable to TOCTOU"
    )


def test_load_does_not_use_path_read_text(tmp_path) -> None:
    """Test that load() does not use Path.read_text() which is vulnerable.

    The fix should use os.open() + os.fdopen() instead.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    db.write_text('[{"id": 1, "text": "valid", "done": false}]', encoding="utf-8")

    # Track if Path.read_text is called (vulnerable approach)
    read_text_calls = [0]
    original_read_text = Path.read_text

    def tracking_read_text(self, *args, **kwargs):
        read_text_calls[0] += 1
        return original_read_text(self, *args, **kwargs)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(Path, "read_text", tracking_read_text)
        storage.load()

    # The fixed code should NOT use Path.read_text() which is vulnerable
    # It should use os.open() + os.fdopen() instead
    assert read_text_calls[0] == 0, (
        "load() should not use Path.read_text() which is vulnerable to TOCTOU. "
        "Should use os.open() with O_NOFOLLOW and read from fd."
    )


def test_load_does_not_use_path_stat(tmp_path) -> None:
    """Test that load() does not use Path.stat() which is vulnerable to TOCTOU.

    The fix should use os.fstat() on the file descriptor instead.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    db.write_text('[{"id": 1, "text": "valid", "done": false}]', encoding="utf-8")

    # Track if Path.stat is called (vulnerable approach)
    stat_calls = [0]
    original_stat = Path.stat

    def tracking_stat(self, *args, **kwargs):
        stat_calls[0] += 1
        return original_stat(self, *args, **kwargs)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(Path, "stat", tracking_stat)
        storage.load()

    # The fixed code should NOT use Path.stat() for the file size check
    # It should use os.fstat() on the file descriptor
    # Note: Path.exists() internally calls stat(), so we expect at least one call
    # The important thing is that the size check uses fstat, not Path.stat
    # This test verifies that the code doesn't call stat() redundantly for size check
    assert stat_calls[0] <= 1, (
        f"load() called Path.stat() {stat_calls[0]} times. "
        "Size check should use os.fstat() on file descriptor, not Path.stat()."
    )


def test_load_oversized_file_still_raises_error(tmp_path) -> None:
    """Test that oversized file check still works after TOCTOU fix."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a file larger than the 10MB limit
    large_content = '{"id": 1, "text": "' + ("x" * (11 * 1024 * 1024)) + '"}'
    db.write_text(large_content, encoding="utf-8")

    with pytest.raises(ValueError, match="too large"):
        storage.load()
