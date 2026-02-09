"""Tests for file backup before overwrites feature (Issue #2468).

This test suite verifies that TodoStorage creates backups of existing files
before overwriting them, with configurable backup behavior.

Feature requirements:
1. When backup=True, create a timestamped backup before overwriting existing files
2. When backup=False (default), no backup is created (backward compatible)
3. Backup filename: <original>.<timestamp>.bak
4. Use shutil.copy2 to preserve file metadata
5. Silently ignore backup failures (don't prevent save)
"""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_file_created_when_saving_to_existing_file(tmp_path) -> None:
    """Test that backup file is created when saving to an existing file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=True)

    # Create initial file
    original_todos = [Todo(id=1, text="original data")]
    storage.save(original_todos)

    # Save again - should create backup
    new_todos = [Todo(id=1, text="new data")]
    storage.save(new_todos)

    # Verify backup file exists
    backups = list(db.parent.glob("todo.json.*.bak"))
    assert len(backups) == 1, f"Expected 1 backup file, found {len(backups)}"

    # Verify backup contains original data
    backup_content = backups[0].read_text(encoding="utf-8")
    assert "original data" in backup_content


def test_backup_disabled_when_backup_false_in_constructor(tmp_path) -> None:
    """Test that backup is not created when backup=False."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=False)

    # Create initial file
    original_todos = [Todo(id=1, text="original data")]
    storage.save(original_todos)

    # Save again - should NOT create backup
    new_todos = [Todo(id=1, text="new data")]
    storage.save(new_todos)

    # Verify no backup file exists
    backups = list(db.parent.glob("todo.json.*.bak"))
    assert len(backups) == 0, f"Expected 0 backup files, found {len(backacks)}"


def test_backup_file_has_correct_timestamp_format(tmp_path) -> None:
    """Test that backup filename contains ISO format timestamp."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=True)

    # Create initial file
    storage.save([Todo(id=1, text="original")])

    # Save again to create backup
    storage.save([Todo(id=1, text="new")])

    # Get backup file
    backups = list(db.parent.glob("todo.json.*.bak"))
    assert len(backups) == 1

    # Verify timestamp format (ISO 8601: YYYY-MM-DDTHH:MM:SS)
    backup_name = backups[0].name
    assert backup_name.startswith("todo.json.")
    assert backup_name.endswith(".bak")

    # Extract timestamp part
    timestamp = backup_name[len("todo.json."):-len(".bak")]
    # ISO format should contain 'T' between date and time
    assert "T" in timestamp, f"Timestamp {timestamp} should be in ISO format"


def test_save_succeeds_even_when_backup_creation_fails(tmp_path) -> None:
    """Test that save succeeds even if backup creation fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=True)

    # Create initial file
    storage.save([Todo(id=1, text="original")])

    # Mock shutil.copy2 to fail
    def failing_copy2(src, dst):
        raise OSError("Backup failed")

    with patch("flywheel.storage.shutil.copy2", failing_copy2):
        # Save should still succeed despite backup failure
        storage.save([Todo(id=1, text="new data")])

    # Verify file was updated (save succeeded)
    loaded = storage.load()
    assert loaded[0].text == "new data"


def test_backup_not_created_on_first_save_when_file_does_not_exist(tmp_path) -> None:
    """Test that backup is not created when file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=True)

    # First save - file doesn't exist yet
    storage.save([Todo(id=1, text="first save")])

    # Verify no backup was created
    backups = list(db.parent.glob("todo.json.*.bak"))
    assert len(backups) == 0, "No backup should be created on first save"


def test_backup_uses_shutil_copy2_for_metadata_preservation(tmp_path) -> None:
    """Test that backup uses shutil.copy2 to preserve file metadata."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=True)

    # Create initial file with specific content
    storage.save([Todo(id=1, text="original")])

    # Mock shutil.copy2 to verify it's called
    with patch("flywheel.storage.shutil.copy2") as mock_copy2:
        storage.save([Todo(id=1, text="new")])

        # Verify shutil.copy2 was called
        mock_copy2.assert_called_once()
        # Verify source and destination paths
        call_args = mock_copy2.call_args
        assert Path(call_args[0][0]) == db  # Source is original file
        assert str(call_args[0][1]).endswith(".bak")  # Dest is backup file


def test_default_backup_is_false_for_backward_compatibility(tmp_path) -> None:
    """Test that default backup=False for backward compatibility."""
    db = tmp_path / "todo.json"

    # Create without specifying backup parameter (default behavior)
    storage = TodoStorage(str(db))

    # Should not create backup by default
    storage.save([Todo(id=1, text="first")])
    storage.save([Todo(id=1, text="second")])

    backups = list(db.parent.glob("todo.json.*.bak"))
    assert len(backups) == 0, "Backup should not be created by default"
