"""Regression tests for issue #4650: Symlink protection in load().

Issue: The load() method uses path.stat() which follows symlinks before
checking file size. This allows an attacker to create a symlink pointing
to sensitive files like /etc/passwd, bypassing security checks.

Security Impact:
- TOCTOU (Time-of-Check-Time-of-Use) vulnerability
- Potential information disclosure through symlink following
- Size check could be bypassed with malicious symlinks

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import os
from pathlib import Path

from flywheel.storage import TodoStorage


def test_load_fails_on_symlink_to_outside_file(tmp_path) -> None:
    """Issue #4650: load() should reject symlinks pointing outside allowed dirs.

    Before fix: load() follows symlink and reads arbitrary files
    After fix: load() should detect symlink and reject it with security error
    """
    # Create a symlink to a sensitive file outside the allowed directory
    symlink_db = tmp_path / "todo.json"
    sensitive_file = tmp_path / "sensitive_data.json"
    # Create valid JSON content that looks like a todo file
    sensitive_file.write_text('[{"id": 1, "text": "SECRET DATA - should not be readable", "done": false}]')

    # Create symlink pointing to the sensitive file
    symlink_db.symlink_to(sensitive_file)

    storage = TodoStorage(str(symlink_db))

    # load() should detect and reject the symlink
    try:
        result = storage.load()
        # If we get here, it means the symlink was followed - security issue!
        # The result would contain sensitive data
        raise AssertionError(
            f"Expected ValueError for symlink path, but load() succeeded and returned: {result}"
        )
    except ValueError as e:
        error_msg = str(e).lower()
        assert "symlink" in error_msg or "symbolic link" in error_msg, (
            f"Expected symlink-related error message, got: {e}"
        )


def test_load_fails_on_symlink_to_system_file(tmp_path) -> None:
    """Issue #4650: load() should reject symlinks to system files.

    This test specifically targets the /etc/passwd attack scenario.
    """
    symlink_db = tmp_path / "todo.json"

    # Create symlink to /etc/passwd if it exists, otherwise use a dummy target
    target = Path("/etc/passwd")
    if target.exists():
        symlink_db.symlink_to(target)
    else:
        # Create a dummy sensitive file if /etc/passwd doesn't exist
        dummy_target = tmp_path / "dummy_sensitive.json"
        dummy_target.write_text('[{"id": 1, "text": "sensitive content", "done": false}]')
        symlink_db.symlink_to(dummy_target)

    storage = TodoStorage(str(symlink_db))

    # load() should detect and reject the symlink
    try:
        result = storage.load()
        raise AssertionError(
            f"Expected ValueError for symlink path, but load() succeeded and returned: {result}"
        )
    except ValueError as e:
        error_msg = str(e).lower()
        assert "symlink" in error_msg or "symbolic link" in error_msg, (
            f"Expected symlink-related error message, got: {e}"
        )


def test_load_succeeds_on_regular_file(tmp_path) -> None:
    """Issue #4650: load() should still work correctly with regular files."""
    db = tmp_path / "todo.json"

    # Create a valid todo file
    db.write_text('[{"id": 1, "text": "test todo", "done": false}]', encoding="utf-8")

    storage = TodoStorage(str(db))
    todos = storage.load()

    assert len(todos) == 1
    assert todos[0].text == "test todo"
    assert todos[0].done is False


def test_load_rejects_broken_symlink(tmp_path) -> None:
    """Issue #4650: load() should reject broken symlinks with clear error."""
    symlink_db = tmp_path / "todo.json"

    # Create symlink to non-existent target
    symlink_db.symlink_to(tmp_path / "nonexistent.json")

    storage = TodoStorage(str(symlink_db))

    # load() should detect and reject the symlink
    try:
        storage.load()
        raise AssertionError("Expected ValueError for broken symlink")
    except ValueError as e:
        error_msg = str(e).lower()
        # Should mention symlink or be a clear security error
        assert "symlink" in error_msg or "symbolic link" in error_msg or "not found" in error_msg, (
            f"Expected symlink or not found error, got: {e}"
        )


def test_load_uses_lstat_not_stat(tmp_path) -> None:
    """Issue #4650: Verify that load() uses lstat() instead of stat().

    This is a white-box test to ensure the implementation doesn't follow symlinks.
    The fix should use os.lstat() or Path.lstat() instead of os.stat() or Path.stat().
    """
    db = tmp_path / "todo.json"
    db.write_text('[{"id": 1, "text": "test", "done": false}]', encoding="utf-8")

    storage = TodoStorage(str(db))

    # Track which os.stat function is called
    original_os_stat = os.stat
    original_os_lstat = os.lstat
    stat_calls = []

    def tracking_os_stat(path, *, dir_fd=None, follow_symlinks=True):
        stat_calls.append(("os.stat", str(path), follow_symlinks))
        return original_os_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    def tracking_os_lstat(path, *, dir_fd=None):
        stat_calls.append(("os.lstat", str(path)))
        return original_os_lstat(path, dir_fd=dir_fd)

    import unittest.mock
    with (
        unittest.mock.patch("os.stat", side_effect=tracking_os_stat),
        unittest.mock.patch("os.lstat", side_effect=tracking_os_lstat),
    ):
        storage.load()

    # After fix: should use lstat or stat with follow_symlinks=False, not stat() that follows symlinks
    # Check that we don't use stat() with follow_symlinks=True (the default)
    stat_follows_symlinks = any(
        call[0] == "os.stat" and call[2] is not False
        for call in stat_calls
        if "todo.json" in call[1]
    )
    lstat_used = any(call[0] == "os.lstat" for call in stat_calls if "todo.json" in call[1])

    # Either lstat should be used, or stat with follow_symlinks=False
    assert lstat_used or not stat_follows_symlinks, (
        f"load() should use lstat() or stat(follow_symlinks=False) to avoid following symlinks. "
        f"Stat calls: {stat_calls}"
    )
