"""Tests for file backup feature before overwrites (issue #2468).

This test suite verifies that TodoStorage.save() creates timestamped backups
of the existing file before each save operation, preventing data loss from
accidental deletion/corruption.
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_file_created_on_save(tmp_path) -> None:
    """Test that a backup file is created when saving to an existing file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Save again - should create backup
    todos = [Todo(id=1, text="updated")]
    storage.save(todos)

    # Check that backup file was created
    backup_files = list(db.parent.glob(".todo.json.*.bak"))
    assert len(backup_files) == 1, f"Expected 1 backup file, found {len(backup_files)}"

    # Verify backup contains original content
    backup_content = backup_files[0].read_text(encoding="utf-8")
    assert '"initial"' in backup_content
    assert '"updated"' not in backup_content


def test_backup_timestamp_format(tmp_path) -> None:
    """Test that backup files have correct timestamp format YYYYMMDD_HHMMSS."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Save again
    todos = [Todo(id=1, text="updated")]
    storage.save(todos)

    # Find backup file and verify timestamp format
    backup_files = list(db.parent.glob(".todo.json.*.bak"))
    assert len(backup_files) == 1

    # Extract timestamp from filename
    filename = backup_files[0].name
    # Pattern: .todo.json.YYYYMMDD_HHMMSS.bak
    match = re.match(rf"\.{db.name}\.(\d{{8}})_\d{{6}}\.bak", filename)
    assert match is not None, f"Backup file {filename} doesn't match expected format"

    timestamp_str = match.group(1)
    # Verify it's a valid date
    datetime.strptime(timestamp_str, "%Y%m%d")


def test_backup_can_be_disabled(tmp_path) -> None:
    """Test that backup can be disabled via constructor parameter."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=False)

    # Create initial file
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Save again - should NOT create backup
    todos = [Todo(id=1, text="updated")]
    storage.save(todos)

    # Check that no backup file was created
    backup_files = list(db.parent.glob(".todo.json.*.bak"))
    assert len(backup_files) == 0


def test_backup_enabled_by_default(tmp_path) -> None:
    """Test that backup is enabled by default when not specified."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Save again
    todos = [Todo(id=1, text="updated")]
    storage.save(todos)

    # Check that backup file was created
    backup_files = list(db.parent.glob(".todo.json.*.bak"))
    assert len(backup_files) == 1


def test_save_succeeds_when_backup_fails(tmp_path) -> None:
    """Test that save succeeds even when backup creation fails."""
    db = tmp_path / "todo.json"

    # Create initial file
    db.write_text('["initial"]', encoding="utf-8")

    storage = TodoStorage(str(db))

    # Mock shutil.copy2 to raise OSError
    with patch("flywheel.storage.shutil.copy2", side_effect=OSError("Backup failed")):
        # Save should still succeed despite backup failure
        todos = [Todo(id=1, text="updated")]
        storage.save(todos)

    # Verify file was updated (save succeeded)
    content = db.read_text(encoding="utf-8")
    assert '"updated"' in content


def test_no_backup_for_new_files(tmp_path) -> None:
    """Test that no backup is created when file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save to new file - should NOT create backup
    todos = [Todo(id=1, text="first")]
    storage.save(todos)

    # Check that no backup file was created
    backup_files = list(db.parent.glob(".todo.json.*.bak"))
    assert len(backup_files) == 0


def test_multiple_backups_created(tmp_path) -> None:
    """Test that multiple saves create multiple backup files."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    todos = [Todo(id=1, text="v1")]
    storage.save(todos)

    # Multiple saves with delay to ensure different timestamps
    for i in range(3):
        todos = [Todo(id=1, text=f"v{i+2}")]
        storage.save(todos)
        time.sleep(1.01)  # Delay to ensure different second-level timestamps

    # Check that multiple backup files were created
    backup_files = list(db.parent.glob(".todo.json.*.bak"))
    assert len(backup_files) == 3


def test_backup_created_in_same_directory(tmp_path) -> None:
    """Test that backup files are created in the same directory as target file."""
    db = tmp_path / "subdir" / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Save again
    todos = [Todo(id=1, text="updated")]
    storage.save(todos)

    # Check that backup file was created in same directory
    backup_files = list(db.parent.glob(".todo.json.*.bak"))
    assert len(backup_files) == 1
    assert backup_files[0].parent == db.parent


def test_backup_preserves_metadata(tmp_path) -> None:
    """Test that backup preserves file metadata using shutil.copy2."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Save again
    todos = [Todo(id=1, text="updated")]
    storage.save(todos)

    # Find backup file
    backup_files = list(db.parent.glob(".todo.json.*.bak"))
    assert len(backup_files) == 1

    # Verify backup content matches original
    backup_content = backup_files[0].read_text(encoding="utf-8")
    assert '"initial"' in backup_content
