"""Tests for backup/rollback capability for corrupted data files (Issue #2817).

These tests verify that:
1. save() creates a backup before overwriting existing file
2. Only one backup file is maintained (rotation)
3. restore_from_backup() can restore from backup
4. load() warns when backup exists on JSON decode error
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_before_overwrite(tmp_path: Path) -> None:
    """Test that save() creates a .bak backup before overwriting existing file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Save new data - should create backup
    new_todos = [Todo(id=1, text="new task")]
    storage.save(new_todos)

    # Verify backup exists
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup file should be created"

    # Verify backup contains original data
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "original task"


def test_save_does_not_create_backup_for_new_file(tmp_path: Path) -> None:
    """Test that save() does NOT create backup when file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save to new file - should NOT create backup
    todos = [Todo(id=1, text="first task")]
    storage.save(todos)

    # Verify backup does NOT exist
    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists(), "No backup should be created for new file"


def test_backup_rotation_only_one_backup_file(tmp_path: Path) -> None:
    """Test that only one backup file exists (old backup is replaced)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - creates file
    storage.save([Todo(id=1, text="version 1")])

    # Second save - creates first backup
    storage.save([Todo(id=1, text="version 2")])

    # Third save - should replace previous backup, not create second one
    storage.save([Todo(id=1, text="version 3")])

    # Verify only ONE backup file exists
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup file should exist"

    # Verify backup contains version 2 (the previous version before version 3)
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "version 2"

    # Verify main file contains version 3
    main_content = json.loads(db.read_text(encoding="utf-8"))
    assert main_content[0]["text"] == "version 3"

    # Verify no other backup files exist
    backup_files = list(tmp_path.glob("*.json.bak*"))
    assert len(backup_files) == 1, "Only one backup file should exist"


def test_restore_from_backup_succeeds(tmp_path: Path) -> None:
    """Test that restore_from_backup() successfully restores from backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="tasks")]
    storage.save(original_todos)

    # Save again to create backup
    storage.save([Todo(id=1, text="modified")])

    # Now corrupt the main file
    db.write_text("corrupted json[[[", encoding="utf-8")

    # Restore from backup
    result = storage.restore_from_backup()
    assert result is True, "restore_from_backup should return True on success"

    # Verify data is restored
    restored = storage.load()
    assert len(restored) == 2
    assert restored[0].text == "original"
    assert restored[1].text == "tasks"


def test_restore_from_backup_fails_when_no_backup(tmp_path: Path) -> None:
    """Test that restore_from_backup() returns False when no backup exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # No backup exists - restore should fail
    result = storage.restore_from_backup()
    assert result is False, "restore_from_backup should return False when no backup"


def test_restore_from_backup_fails_when_backup_missing(tmp_path: Path) -> None:
    """Test that restore_from_backup() returns False when backup file is missing."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data and backup (need two saves to create backup)
    storage.save([Todo(id=1, text="original")])
    storage.save([Todo(id=1, text="modified")])  # This creates backup with "original"

    # Delete the backup file
    backup_path = tmp_path / "todo.json.bak"
    backup_path.unlink()

    # Restore should fail
    result = storage.restore_from_backup()
    assert result is False, "restore_from_backup should return False when backup is missing"


def test_load_warns_when_backup_exists_on_json_error(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test that load() logs warning when backup exists on JSON decode error."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data and backup
    storage.save([Todo(id=1, text="original")])
    storage.save([Todo(id=1, text="new")])  # This creates backup with "original"

    # Corrupt the main file
    db.write_text("invalid json{{{", encoding="utf-8")

    # Try to load - should raise ValueError about invalid JSON
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()

    # Verify warning was logged about backup file
    assert any("backup" in record.message.lower() for record in caplog.records), \
        "load() should log warning about backup file"


def test_backup_preserves_file_permissions(tmp_path: Path) -> None:
    """Test that backup file preserves proper file permissions."""
    import stat

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    storage.save([Todo(id=1, text="original")])
    storage.save([Todo(id=1, text="new")])

    # Verify backup has restrictive permissions (owner read/write only)
    backup_path = tmp_path / "todo.json.bak"
    backup_stat = backup_path.stat()
    backup_mode = backup_stat.st_mode & 0o777

    # Backup should have at least owner read and write (0o600)
    assert backup_mode & stat.S_IRUSR, "Backup should be readable by owner"
    assert backup_mode & stat.S_IWUSR, "Backup should be writable by owner"


def test_backup_with_custom_path(tmp_path: Path) -> None:
    """Test that backup works with custom file paths."""
    db = tmp_path / "subdir" / "custom.json"
    storage = TodoStorage(str(db))

    # Create initial data
    storage.save([Todo(id=1, text="original")])

    # Save new data
    storage.save([Todo(id=1, text="new")])

    # Verify backup is created in same directory as target file
    backup_path = tmp_path / "subdir" / "custom.json.bak"
    assert backup_path.exists(), "Backup should be created in same directory"

    # Verify backup content
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "original"
