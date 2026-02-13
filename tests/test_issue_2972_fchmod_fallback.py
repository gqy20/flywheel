"""Regression tests for issue #2972: fchmod error handling on unsupported filesystems.

Issue: os.fchmod can fail on some filesystems (FAT32, network mounts) or when
the fd is invalidated. The save() method should not crash and should gracefully
fallback to chmod(path) after the file is written.

Security requirement: We still want to set 0o600 permissions, but if fchmod fails,
we should try chmod as a fallback and log a warning.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import logging
import os
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_completes_when_fchmod_raises_oserror(tmp_path) -> None:
    """Issue #2972: save() should complete even when os.fchmod fails.

    On filesystems that don't support permissions (FAT32, network mounts),
    os.fchmod may raise OSError. The save operation should still complete
    successfully, possibly with a fallback to chmod after the file is written.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test todo")]

    def failing_fchmod(fd, mode):
        raise OSError(1, "Operation not permitted")

    with patch("flywheel.storage.os.fchmod", failing_fchmod):
        # save() should NOT crash when fchmod fails
        # It should either: 1) handle the error gracefully, or 2) fallback to chmod
        storage.save(todos)

    # Verify the data was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_temp_file_cleanup_when_fchmod_fails(tmp_path) -> None:
    """Issue #2972: Temp file cleanup should still work when fchmod fails.

    If fchmod fails and causes any issue, temp files should still be cleaned up.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Get initial temp files count
    initial_temp_files = list(tmp_path.glob(".*.json.*.tmp"))

    def failing_fchmod(fd, mode):
        raise OSError(1, "Operation not permitted")

    with patch("flywheel.storage.os.fchmod", failing_fchmod):
        storage.save([Todo(id=1, text="test")])

    # Count temp files after save - should not have leftover temp files
    final_temp_files = list(tmp_path.glob(".*.json.*.tmp"))
    # Filter out any that existed before
    new_temp_files = [f for f in final_temp_files if f not in initial_temp_files]

    assert len(new_temp_files) == 0, (
        f"Temp files not cleaned up: {new_temp_files}"
    )


def test_fchmod_fallback_to_chmod_on_path(tmp_path) -> None:
    """Issue #2972: When fchmod fails, should fallback to chmod(path).

    This verifies that even when os.fchmod fails, we still attempt to set
    permissions using chmod on the file path after it's written.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    chmod_calls = []

    def failing_fchmod(fd, mode):
        chmod_calls.append(("fchmod_failed", fd, mode))
        raise OSError(1, "Operation not permitted")

    def tracking_chmod(path, mode, *, dir_fd=None, follow_symlinks=True):
        chmod_calls.append(("chmod", str(path), mode))

    with patch("flywheel.storage.os.fchmod", failing_fchmod), patch("flywheel.storage.os.chmod", tracking_chmod):
        storage.save([Todo(id=1, text="test")])

    # Either fchmod succeeded, or we fell back to chmod
    # If fchmod failed (which it does in our mock), chmod should have been called
    fchmod_failed = any(call[0] == "fchmod_failed" for call in chmod_calls)

    if fchmod_failed:
        # We should have attempted chmod as a fallback
        chmod_attempts = [call for call in chmod_calls if call[0] == "chmod"]
        assert len(chmod_attempts) > 0, (
            "fchmod failed but chmod fallback was not attempted"
        )
        # The chmod should have been called with 0o600
        for call in chmod_attempts:
            assert call[2] == 0o600, (
                f"chmod called with wrong mode: {oct(call[2])}, expected 0o600"
            )


def test_normal_unix_filesystem_uses_fchmod(tmp_path) -> None:
    """Issue #2972: On normal Unix filesystems, fchmod should still be used.

    This test verifies that the fix doesn't break the normal case where
    fchmod works correctly.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    fchmod_calls = []

    original_fchmod = os.fchmod

    def tracking_fchmod(fd, mode):
        fchmod_calls.append((fd, mode))
        # Actually perform the chmod for real behavior
        original_fchmod(fd, mode)

    with patch("flywheel.storage.os.fchmod", tracking_fchmod):
        storage.save([Todo(id=1, text="test")])

    # fchmod should have been called with 0o600
    assert len(fchmod_calls) > 0, "fchmod was not called"
    for _fd, mode in fchmod_calls:
        assert mode == 0o600, f"fchmod called with wrong mode: {oct(mode)}"


def test_save_succeeds_with_fallback_when_both_fail(tmp_path, caplog) -> None:
    """Issue #2972: Save should succeed even when both fchmod and chmod fail.

    This is the most extreme case - the filesystem doesn't support permissions
    at all. The save should still succeed, but a warning should be logged.
    """
    caplog.set_level(logging.WARNING)

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    def failing_fchmod(fd, mode):
        raise OSError(1, "Operation not permitted")

    def failing_chmod(path, mode, *, dir_fd=None, follow_symlinks=True):
        raise OSError(1, "Operation not permitted")

    with patch("flywheel.storage.os.fchmod", failing_fchmod), patch("flywheel.storage.os.chmod", failing_chmod):
        # Should not raise - save should still complete
        storage.save([Todo(id=1, text="test")])

    # Verify data was saved
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"

    # A warning should have been logged about permission failure
    assert any("Could not set file permissions" in record.message for record in caplog.records), (
        "Expected warning about permission failure was not logged"
    )
