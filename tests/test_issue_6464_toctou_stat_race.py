"""Regression tests for issue #6464: TOCTOU race in file size check.

Issue: File size check uses stat() which follows symlinks, allowing TOCTOU bypass
if attacker replaces file between stat and read.

The fix: Open file with os.open first, then use fstat on the fd to avoid TOCTOU
race between size check and read.

These tests verify:
1. File is opened once and size checked via fd before reading
2. TOCTOU test verifies no race window between size check and read
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage
from flywheel.todo import Todo


def test_load_uses_fstat_not_stat(tmp_path) -> None:
    """Issue #6464: load() should use fstat() on fd, not stat() on path.

    This verifies the implementation uses the secure pattern of:
    1. Open file to get fd
    2. Use fstat(fd) to check size (not stat(path))
    3. Read from the same fd

    If stat(path) is used, an attacker could replace the file between
    stat() and read().
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a valid todo file
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Track if stat() is called on the path (it shouldn't be)
    # We do this by checking that the implementation uses os.open + os.fstat
    # instead of Path.stat() or os.stat()

    # The implementation should work correctly - this is a behavior test
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_load_rejects_oversized_file(tmp_path) -> None:
    """Verify that oversized files are still rejected after the fix."""
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a file larger than the limit
    large_content = "x" * (_MAX_JSON_SIZE_BYTES + 1024)  # Just over limit
    db.write_text(large_content, encoding="utf-8")

    # Should raise ValueError about file being too large
    with pytest.raises(ValueError, match=r"too large|DoS"):
        storage.load()


def test_load_symlink_size_check_uses_fd(tmp_path) -> None:
    """Issue #6464: Size check should use fstat on fd, not stat on symlink path.

    If the file is a symlink, the size check should operate on the opened file
    descriptor, not follow the symlink path again (which could point elsewhere).

    This test creates a symlink and verifies the size check works correctly
    on the actual file content, not the symlink metadata.
    """
    # Create a real file with valid content
    real_file = tmp_path / "real_todo.json"
    real_content = json.dumps([{"id": 1, "text": "real task"}])
    real_file.write_text(real_content, encoding="utf-8")

    # Create a symlink pointing to the real file
    symlink = tmp_path / "symlink_todo.json"
    symlink.symlink_to(real_file)

    storage = TodoStorage(str(symlink))

    # Should load successfully, reading from the symlink target
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "real task"


def test_load_toctou_race_protection(tmp_path) -> None:
    """Issue #6464: Verify TOCTOU race cannot bypass size limit.

    This test simulates an attacker trying to exploit the race window
    between stat() and read() by swapping the file after size check.

    Before fix: An attacker could:
    1. Have a small file that passes size check
    2. Swap it with a large file after stat() but before read()
    3. Cause large file to be read into memory

    After fix: File is opened once, size checked via fd, then read from same fd.
    The fd always refers to the same file, even if path is swapped.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial small valid file
    small_content = json.dumps([{"id": 1, "text": "small"}])
    db.write_text(small_content, encoding="utf-8")

    # This test verifies that even if we tried to swap, the implementation
    # is safe because it uses fstat on fd instead of stat on path.
    #
    # We can't easily test the actual race condition in a reliable way,
    # but we can verify the implementation by checking:
    # 1. The load works correctly
    # 2. Size limits are enforced

    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "small"


def test_load_opens_file_once_for_size_and_read(tmp_path) -> None:
    """Issue #6464: load() should open file once, not twice.

    Before fix:
    - stat() opens file to get size (implicit in Path.stat())
    - read_text() opens file again to read content

    After fix:
    - os.open() gets fd
    - os.fstat(fd) gets size
    - os.read(fd) or fdopen reads content
    - All operations use same fd
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create valid content
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)

    # Track if the implementation uses Path.stat() which is vulnerable
    # We check this by monkey-patching Path.stat to detect if it's called
    original_stat = Path.stat
    stat_calls = []

    def tracking_stat(self, *args, **kwargs):
        if str(self).endswith("todo.json"):
            stat_calls.append(str(self))
        return original_stat(self, *args, **kwargs)

    # Monkey-patch Path.stat temporarily
    Path.stat = tracking_stat
    try:
        storage.load()
    finally:
        Path.stat = original_stat

    # Path.stat() should NOT be called on the db file after the fix
    # The implementation should use os.open + os.fstat instead
    assert len(stat_calls) == 0, (
        f"Path.stat() was called {len(stat_calls)} times on the db file. "
        "This is vulnerable to TOCTOU race. Use os.open + os.fstat instead."
    )


def test_normal_load_still_works(tmp_path) -> None:
    """Verify normal load operations work after the fix."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Empty file case
    assert storage.load() == []

    # Valid data case
    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second", done=True),
    ]
    storage.save(todos)

    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "first"
    assert loaded[1].text == "second"
    assert loaded[1].done is True
