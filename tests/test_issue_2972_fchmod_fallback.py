"""Regression tests for issue #2972: fchmod OSError handling and fallback.

Issue: os.fchmod can fail silently or raise OSError on some filesystems
(FAT32, network mounts) that don't support Unix permissions. The save()
function should gracefully handle this case.

The fix should:
1. Wrap os.fchmod in try/except to handle OSError gracefully
2. Log a warning when permissions cannot be set
3. Fall back to chmod(path) after file is written
4. Still allow save() to complete successfully on unsupported filesystems

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path
from unittest import mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_completes_when_fchmod_raises_oserror(tmp_path) -> None:
    """Issue #2972: save() should not crash when os.fchmod raises OSError.

    This simulates a filesystem that doesn't support Unix permissions (e.g., FAT32,
    network mounts) where fchmod would fail.

    Before fix: save() crashes with OSError when fchmod fails
    After fix: save() completes successfully, warning is logged
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    def failing_fchmod(fd, mode):
        raise OSError(95, "Operation not supported", f"fd {fd}")

    with mock.patch.object(os, "fchmod", failing_fchmod):
        # save() should NOT raise an exception
        storage.save([Todo(id=1, text="test")])

    # Verify the file was still saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"


def test_temp_file_cleanup_when_fchmod_fails(tmp_path) -> None:
    """Issue #2972: Temp file should be cleaned up even if fchmod fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track temp files
    temp_files_created = []

    original_mkstemp = tempfile.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(Path(path))
        return fd, path

    def failing_fchmod(fd, mode):
        raise OSError(95, "Operation not supported")

    with (
        mock.patch.object(tempfile, "mkstemp", tracking_mkstemp),
        mock.patch.object(os, "fchmod", failing_fchmod),
    ):
        storage.save([Todo(id=1, text="test")])

    # Temp files should be cleaned up (renamed to final destination)
    for temp_file in temp_files_created:
        assert not temp_file.exists(), f"Temp file not cleaned up: {temp_file}"

    # Final file should exist
    assert db.exists()


def test_warning_logged_when_fchmod_fails(tmp_path, caplog) -> None:
    """Issue #2972: A warning should be logged when permissions cannot be set."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    def failing_fchmod(fd, mode):
        raise OSError(95, "Operation not supported")

    import logging

    caplog.set_level(logging.WARNING)

    with mock.patch.object(os, "fchmod", failing_fchmod):
        storage.save([Todo(id=1, text="test")])

    # A warning should have been logged about permission failure
    assert any(
        "permission" in record.message.lower() or "chmod" in record.message.lower()
        for record in caplog.records
        if record.levelno >= logging.WARNING
    ), f"Expected warning about permission, got: {[r.message for r in caplog.records]}"


def test_fchmod_fallback_attempts_chmod_on_path(tmp_path) -> None:
    """Issue #2972: When fchmod fails, should attempt chmod(path) as fallback."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    chmod_path_calls = []

    original_chmod = os.chmod

    def failing_fchmod(fd, mode):
        raise OSError(95, "Operation not supported")

    def tracking_chmod(path, mode, *args, **kwargs):
        chmod_path_calls.append((str(path), mode))
        return original_chmod(path, mode, *args, **kwargs)

    with (
        mock.patch.object(os, "fchmod", failing_fchmod),
        mock.patch.object(os, "chmod", tracking_chmod),
    ):
        storage.save([Todo(id=1, text="test")])

    # Should have attempted chmod on the path as a fallback
    assert len(chmod_path_calls) >= 1, f"Expected chmod path call, got: {chmod_path_calls}"
    # The mode should be 0o600
    assert chmod_path_calls[0][1] == 0o600, f"Expected mode 0o600, got {oct(chmod_path_calls[0][1])}"


def test_normal_filesystems_still_get_0o600_permissions(tmp_path) -> None:
    """Issue #2972: Normal Unix filesystems should still get 0o600 permissions.

    This test ensures the fix doesn't break the existing behavior on normal filesystems.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    # On a normal filesystem, permissions should be 0o600
    file_mode = stat.S_IMODE(db.stat().st_mode)
    assert file_mode == 0o600, f"Expected mode 0o600, got {oct(file_mode)}"


def test_save_works_when_both_fchmod_and_chmod_fail(tmp_path) -> None:
    """Issue #2972: save() should still work even if both fchmod and chmod fail.

    This simulates a truly restrictive filesystem where neither method works.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    def always_failing_fchmod(fd, mode):
        raise OSError(95, "Operation not supported")

    def always_failing_chmod(path, mode, *args, **kwargs):
        raise OSError(95, "Operation not supported")

    with (
        mock.patch.object(os, "fchmod", always_failing_fchmod),
        mock.patch.object(os, "chmod", always_failing_chmod),
    ):
        # save() should NOT crash - it should complete with a warning
        storage.save([Todo(id=1, text="test")])

    # The file should still be saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test"
