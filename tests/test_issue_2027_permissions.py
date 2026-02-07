"""Test for issue #2027: temp file permissions should be exactly 0o600.

This test verifies the security promise made in the docstring that temp files
are created with 0o600 permissions (owner read/write only), not 0o700
(which includes execute permission).
"""
from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_temp_file_has_exactly_0o600_permissions(tmp_path: Path) -> None:
    """Temp files created during save must have exactly 0o600 permissions.

    Issue #2027: The code promised 0o600 in the docstring but actually set
    0o700 (via stat.S_IRWXU), which includes execute permission.

    This test ensures that temp files are created with exactly 0o600
    (S_IRUSR | S_IWUSR = 0o600 = rw-------), matching the security promise.
    """
    # Set up TodoStorage with a path in our temp directory
    db_path = tmp_path / "test.json"
    storage = TodoStorage(str(db_path))

    # Create a temp directory to monitor for temp file creation
    # The save() method creates temp files in the same dir as the target file
    temp_files_before = set(tmp_path.glob("*.tmp"))

    # Save a todo - this creates a temp file
    todos = [Todo(id=1, text="Test todo")]
    storage.save(todos)

    # Find the newly created temp file (it should be cleaned up after rename)
    # Since the temp file is renamed and then deleted, we need to catch it during save
    # We'll do this by mocking os.replace to inspect the temp file before it's replaced

    # Alternative approach: monkeypatch os.replace to check permissions before replacing
    original_replace = os.replace
    captured_temp_path: Path | None = None
    captured_perms: int | None = None

    def mock_replace(src: str, dst: str) -> None:
        nonlocal captured_temp_path, captured_perms
        captured_temp_path = Path(src)
        # Get file permissions before replacement
        stat_info = os.stat(src)
        captured_perms = stat.S_IMODE(stat_info.st_mode)
        # Call original to complete the operation
        return original_replace(src, dst)

    # Patch os.replace for this test
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(os, "replace", mock_replace)

    try:
        # Save again with our monkeypatch in place
        storage.save(todos)

        # Verify we captured the temp file permissions
        assert captured_temp_path is not None, "Temp file was not created"
        assert captured_perms is not None, "Could not capture temp file permissions"

        # The critical assertion: permissions must be exactly 0o600
        # 0o600 = rw------- (read and write for owner only)
        # This is NOT 0o700 = rwx------ (which includes execute)
        assert captured_perms == 0o600, (
            f"Temp file permissions are 0o{captured_perms:03o}, expected 0o600. "
            f"The security promise in the docstring requires owner read/write only, "
            f"without execute permission. stat.S_IRWXU (0o700) includes execute."
        )
    finally:
        monkeypatch.undo()


def test_temp_file_no_execute_bit_set(tmp_path: Path) -> None:
    """Temp files must NOT have execute permission set for owner.

    This is a more targeted test that specifically checks for the absence
    of the execute bit, which is the core issue in #2027.
    """
    db_path = tmp_path / "test.json"
    storage = TodoStorage(str(db_path))

    original_replace = os.replace
    captured_perms: int | None = None

    def mock_replace(src: str, dst: str) -> None:
        nonlocal captured_perms
        stat_info = os.stat(src)
        captured_perms = stat.S_IMODE(stat_info.st_mode)
        return original_replace(src, dst)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(os, "replace", mock_replace)

    try:
        todos = [Todo(id=1, text="Test")]
        storage.save(todos)

        assert captured_perms is not None

        # Check that execute bit is NOT set
        has_execute = bool(captured_perms & stat.S_IXUSR)
        assert not has_execute, (
            f"Temp file has execute permission set (0o{captured_perms:03o}). "
            f"This violates the security promise of 0o600 (read/write only). "
            f"Use stat.S_IRUSR | stat.S_IWUSR instead of stat.S_IRWXU."
        )
    finally:
        monkeypatch.undo()


def test_temp_file_has_read_write_for_owner_only(tmp_path: Path) -> None:
    """Temp files should have exactly read and write bits for owner.

    This verifies the correct permission composition: S_IRUSR | S_IWUSR
    """
    db_path = tmp_path / "test.json"
    storage = TodoStorage(str(db_path))

    original_replace = os.replace
    captured_perms: int | None = None

    def mock_replace(src: str, dst: str) -> None:
        nonlocal captured_perms
        stat_info = os.stat(src)
        captured_perms = stat.S_IMODE(stat_info.st_mode)
        return original_replace(src, dst)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(os, "replace", mock_replace)

    try:
        todos = [Todo(id=1, text="Test")]
        storage.save(todos)

        assert captured_perms is not None

        # Verify exact permission bits
        expected = stat.S_IRUSR | stat.S_IWUSR  # 0o600
        assert captured_perms == expected, (
            f"Expected permissions 0o{expected:03o} (S_IRUSR | S_IWUSR), "
            f"got 0o{captured_perms:03o}"
        )
    finally:
        monkeypatch.undo()
