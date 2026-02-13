"""Regression tests for issue #2972: save() should handle fchmod failures gracefully.

Issue: os.fchmod can fail on some filesystems (FAT32, network mounts) that don't
support Unix permissions. The current code has no fallback, causing save() to crash.

Security requirements:
- On filesystems that don't support permissions, save() should not crash
- Warning should be logged if permissions cannot be set to 0o600
- Normal Unix filesystems should still get 0o600 permissions

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import stat
from pathlib import Path
from unittest import mock

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_handles_fchmod_failure_gracefully(tmp_path) -> None:
    """Issue #2972: save() should complete even when fchmod raises OSError.

    On filesystems like FAT32 that don't support Unix permissions, os.fchmod
    will raise OSError. The save() function should handle this gracefully
    and still complete the write operation.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Mock os.fchmod to simulate filesystem that doesn't support permissions
    with mock.patch("os.fchmod") as mock_fchmod:
        mock_fchmod.side_effect = OSError("Operation not supported")

        # save() should NOT raise an exception even when fchmod fails
        storage.save([Todo(id=1, text="test fchmod failure")])

    # Verify the file was still written correctly
    assert db.exists(), "Database file should exist after save()"
    content = db.read_text()
    assert "test fchmod failure" in content


def test_save_temp_file_cleanup_on_fchmod_failure(tmp_path) -> None:
    """Issue #2972: Temp files should be cleaned up when fchmod fails.

    Even if fchmod fails (before any data is written), the temp file
    should be cleaned up properly to avoid leaving orphaned files.
    """
    import tempfile as tempfile_module

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track created temp files
    temp_files_created = []
    original_mkstemp = tempfile_module.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(Path(path))
        return fd, path

    with mock.patch("tempfile.mkstemp", tracking_mkstemp), mock.patch(
        "os.fchmod"
    ) as mock_fchmod:
        # Make fchmod fail
        mock_fchmod.side_effect = OSError("Operation not supported")

        storage.save([Todo(id=1, text="test")])

    # Verify temp files were created but cleaned up
    for temp_file in temp_files_created:
        assert not temp_file.exists(), (
            f"Temp file {temp_file} should be cleaned up after save() completes"
        )

    # The actual db file should exist
    assert db.exists(), "Database file should exist after save()"


def test_save_logs_warning_on_fchmod_failure(tmp_path, caplog) -> None:
    """Issue #2972: A warning should be logged when permissions cannot be set.

    When os.fchmod fails, the user should be warned that the file may have
    less restrictive permissions than intended (0o600).
    """
    import logging

    caplog.set_level(logging.WARNING)

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    with mock.patch("os.fchmod") as mock_fchmod:
        mock_fchmod.side_effect = OSError("Operation not supported")

        storage.save([Todo(id=1, text="test warning")])

    # Verify a warning was logged about permissions
    warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warning_records) > 0, (
        "Expected a warning to be logged when file permissions cannot be set"
    )

    # The warning should mention permissions
    warning_messages = [r.message for r in warning_records]
    assert any("permission" in msg.lower() for msg in warning_messages), (
        f"Warning should mention permissions. Got: {warning_messages}"
    )


def test_save_uses_chmod_fallback_when_fchmod_fails(tmp_path) -> None:
    """Issue #2972: When fchmod fails, chmod should be attempted as fallback.

    After the file is closed (fdopen context), chmod() should be tried
    as a fallback to set permissions on the final path.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    chmod_calls = []

    def mock_chmod(path, mode, *args, **kwargs):
        chmod_calls.append((str(path), mode))
        # Don't actually change permissions in test

    with mock.patch("os.fchmod") as mock_fchmod:
        mock_fchmod.side_effect = OSError("Operation not supported")
        with mock.patch("os.chmod", side_effect=mock_chmod):
            storage.save([Todo(id=1, text="test fallback")])

    # Verify chmod was called as fallback
    assert len(chmod_calls) > 0, (
        "os.chmod should be called as fallback when os.fchmod fails"
    )

    # Verify chmod was called with correct mode (0o600)
    for _path, mode in chmod_calls:
        assert mode == stat.S_IRUSR | stat.S_IWUSR, (
            f"chmod should be called with 0o600, got {oct(mode)}"
        )
