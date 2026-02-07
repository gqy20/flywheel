"""Regression test for issue #1999: Symlink attack vulnerability in atomic save.

This test suite verifies that TodoStorage.save() is protected against symlink attacks:
1. Temp file path is unpredictable (random name)
2. Temp file has restrictive permissions (0o600)
3. Pre-existing symlinks at temp path are handled safely

Security issue: An attacker could pre-create a predictable temp file path
(.todo.json.tmp) as a symlink to cause writes to arbitrary locations.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_temp_file_name_is_unpredictable(tmp_path) -> None:
    """Test that temp file name contains random component, not just predictable prefix.

    Vulnerability: Using '.todo.json.tmp' is predictable - attacker can pre-create
    this path before the save operation.

    Fix: tempfile.mkstemp adds random suffix making name unpredictable.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]
    temp_files_created = []

    # Track what temp file names are created
    original_mkstemp = tempfile.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(Path(path))
        return fd, path

    with patch("tempfile.mkstemp", side_effect=tracking_mkstemp):
        storage.save(todos)

    # Verify temp file was created with random name
    assert len(temp_files_created) == 1, "Should create exactly one temp file"
    temp_name = temp_files_created[0].name

    # Name should contain random characters (not just '.todo.json.tmp')
    # tempfile.mkstemp uses pattern like .todo.json.XXXXXX
    assert ".todo.json." in temp_name, "Should contain original filename prefix"
    assert temp_name != ".todo.json.tmp", "Should NOT be just '.todo.json.tmp'"
    assert len(temp_name) > len(".todo.json.tmp"), "Random suffix should add length"


def test_temp_file_has_restrictive_permissions(tmp_path) -> None:
    """Test that temp file is created with mode 0o600 (owner read/write only).

    Vulnerability: write_text uses default umask, potentially readable by others
    before atomic rename.

    Fix: os.chmod(0o600) is called on temp file after mkstemp to ensure
    restrictive permissions.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="sensitive data")]

    # Track chmod calls to verify 0o600 is set
    chmod_calls = []
    original_chmod = os.chmod

    def tracking_chmod(path, mode):
        chmod_calls.append((Path(path), mode))
        return original_chmod(path, mode)

    with patch("os.chmod", side_effect=tracking_chmod):
        storage.save(todos)

    # Verify chmod was called with 0o600 on the temp file
    assert len(chmod_calls) >= 1, "os.chmod should be called"
    temp_chmod = [c for c in chmod_calls if ".todo.json" in str(c[0])]

    assert len(temp_chmod) >= 1, "os.chmod should be called on temp file"
    _, mode = temp_chmod[0]
    assert mode == 0o600, f"Temp file should have mode 0o600, got {oct(mode)}"


def test_symlink_at_predictable_path_is_safe(tmp_path) -> None:
    """Test that pre-existing symlink at predictable path is handled safely.

    Vulnerability: Attacker pre-creates '.todo.json.tmp' as symlink to
    sensitive file like '/etc/passwd'. When we write to temp file, we
    overwrite the symlink target.

    Fix: Use random temp name (unpredictable) so attacker cannot guess path.
    Even if symlink exists at one random name, probability of collision is negligible.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a sensitive target file (simulating /etc/passwd or similar)
    sensitive_file = tmp_path / "sensitive.txt"
    sensitive_file.write_text("ORIGINAL_SENSITIVE_CONTENT", encoding="utf-8")

    # Attacker tries to pre-create the OLD predictable temp path as symlink
    predictable_temp_path = tmp_path / ".todo.json.tmp"

    # On systems supporting symlinks, test the fix
    if hasattr(os, "symlink"):
        try:
            predictable_temp_path.symlink_to(sensitive_file)

            # Save should succeed because we use RANDOM temp name,
            # not the predictable '.todo.json.tmp'
            todos = [Todo(id=1, text="test")]
            storage.save(todos)

            # Verify sensitive file was NOT overwritten
            assert sensitive_file.read_text(encoding="utf-8") == "ORIGINAL_SENSITIVE_CONTENT"

            # Verify our actual file was written correctly
            loaded = storage.load()
            assert len(loaded) == 1
            assert loaded[0].text == "test"

        except OSError as e:
            # Symlink creation failed (e.g., permissions on Windows)
            # Skip this specific check but verify basic functionality
            pytest.skip(f"Cannot create symlinks: {e}")
    else:
        pytest.skip("Platform does not support symlinks")


def test_tempfile_mkstemp_is_used_for_save(tmp_path) -> None:
    """Test that save() uses tempfile.mkstemp instead of predictable temp path.

    This is a direct test that the fix is in place.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test")]

    # Mock tempfile.mkstemp to verify it's called with correct arguments
    # We need to use a spy that records the call but still executes
    original_mkstemp = tempfile.mkstemp
    calls = []

    def spy_mkstemp(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return original_mkstemp(*args, **kwargs)

    with patch("tempfile.mkstemp", side_effect=spy_mkstemp):
        storage.save(todos)

    # Verify tempfile.mkstemp was called
    assert len(calls) == 1, "tempfile.mkstemp should be called exactly once"

    call_kwargs = calls[0]["kwargs"]

    # Verify dir parameter points to same directory as target file
    assert "dir" in call_kwargs
    assert call_kwargs["dir"] == db.parent

    # Verify prefix contains original filename (for identifiability)
    assert "prefix" in call_kwargs
    assert ".todo.json" in call_kwargs["prefix"]
