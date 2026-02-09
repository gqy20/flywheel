"""Tests for file backup before save operations (Issue #2522).

This test suite verifies that TodoStorage creates backups before save operations
to prevent permanent data loss from application bugs writing corrupted data.
"""

from __future__ import annotations

import re

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_created_on_save_when_file_exists(tmp_path) -> None:
    """Test that a backup file with timestamp is created before save overwrites existing file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    original_todos = [Todo(id=1, text="original data")]
    storage.save(original_todos)

    # Save new data (should create backup)
    new_todos = [Todo(id=2, text="new data")]
    storage.save(new_todos)

    # Verify backup was created
    backups = storage.list_backups()
    assert len(backups) == 1, "One backup should be created"

    # Verify backup contains original data
    backup_path = backups[0]
    backup_storage = TodoStorage(str(backup_path))
    backup_data = backup_storage.load()
    assert len(backup_data) == 1
    assert backup_data[0].text == "original data"


def test_backup_rotation_removes_old_backups(tmp_path) -> None:
    """Test that only max_backups (default 3) are kept."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), max_backups=3)

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Perform 5 saves to create 5 backups
    for i in range(5):
        storage.save([Todo(id=i + 2, text=f"save {i}")])

    # Verify only 3 most recent backups are kept
    backups = storage.list_backups()
    assert len(backups) == 3, "Only max_backups (3) should be kept"


def test_list_backups_returns_available_backups(tmp_path) -> None:
    """Test that list_backups() returns sorted list of backup files."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Create multiple backups
    for i in range(3):
        storage.save([Todo(id=i + 2, text=f"save {i}")])

    # Get backups
    backups = storage.list_backups()

    # Verify backups are returned
    assert len(backups) == 3

    # Verify backups contain timestamps in filename
    for backup in backups:
        match = re.search(r"\d{8}T\d{6}_\d+", backup.name)
        assert match, f"Backup filename should contain timestamp: {backup.name}"

    # Verify backups are sorted by mtime (newest first)
    # The list_backups() method uses st_mtime sorting
    mtimes = [b.stat().st_mtime for b in backups]
    assert mtimes == sorted(mtimes, reverse=True), "Backups should be sorted newest first"


def test_restore_from_backup(tmp_path) -> None:
    """Test that restore() correctly restores data from a specific backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    original_todos = [Todo(id=1, text="backup data"), Todo(id=2, text="backup task 2")]
    storage.save(original_todos)

    # Save new data (creates backup)
    storage.save([Todo(id=3, text="current data")])

    # Get backup
    backups = storage.list_backups()
    assert len(backups) == 1
    backup_path = backups[0]

    # Restore from backup
    storage.restore(backup_path)

    # Verify restored data matches backup
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "backup data"
    assert loaded[1].text == "backup task 2"


def test_backup_can_be_disabled(tmp_path) -> None:
    """Test that backup can be disabled via enable_backups=False."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=False)

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Save new data (should NOT create backup)
    storage.save([Todo(id=2, text="new data")])

    # Verify no backups were created
    backups = storage.list_backups()
    assert len(backups) == 0, "No backups should be created when disabled"


def test_no_backup_when_file_does_not_exist(tmp_path) -> None:
    """Test that no backup is created for new files (first save)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save to non-existent file
    storage.save([Todo(id=1, text="first save")])

    # Verify no backups were created
    backups = storage.list_backups()
    assert len(backups) == 0, "No backup should be created for new files"


def test_custom_max_backups_respected(tmp_path) -> None:
    """Test that custom max_backups value is respected."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), max_backups=5)

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Perform 10 saves
    for i in range(10):
        storage.save([Todo(id=i + 2, text=f"save {i}")])

    # Verify only 5 backups are kept
    backups = storage.list_backups()
    assert len(backups) == 5, "Custom max_backups (5) should be respected"


def test_backup_preserves_file_permissions(tmp_path) -> None:
    """Test that backup preserves the original file's content correctly."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create file with unicode and special characters
    original_todos = [
        Todo(id=1, text="unicode: 你好"),
        Todo(id=2, text='quotes: "test"'),
        Todo(id=3, text="newlines\nand\ttabs"),
    ]
    storage.save(original_todos)

    # Save new data
    storage.save([Todo(id=4, text="new")])

    # Verify backup contains exact original data
    backups = storage.list_backups()
    assert len(backups) == 1

    backup_storage = TodoStorage(str(backups[0]))
    backup_data = backup_storage.load()

    assert len(backup_data) == 3
    assert backup_data[0].text == "unicode: 你好"
    assert backup_data[1].text == 'quotes: "test"'
    assert backup_data[2].text == "newlines\nand\ttabs"


def test_restore_nonexistent_backup_raises_error(tmp_path) -> None:
    """Test that restoring from non-existent backup raises an error."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Try to restore from non-existent backup
    fake_backup = tmp_path / "nonexistent_backup.json"

    with pytest.raises(ValueError, match="Backup file not found"):
        storage.restore(fake_backup)


def test_backup_directory_structure(tmp_path) -> None:
    """Test that backups are stored in the correct location (.backups subdirectory)."""
    db = tmp_path / "subdir" / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Save new data (creates backup)
    storage.save([Todo(id=2, text="new")])

    # Verify backup directory exists
    backup_dir = tmp_path / "subdir" / ".backups"
    assert backup_dir.exists(), "Backup directory should exist"
    assert backup_dir.is_dir(), "Backup should be a directory"

    # Verify backup is in the correct location
    backups = storage.list_backups()
    assert len(backups) == 1
    assert backups[0].parent == backup_dir, "Backup should be in .backups subdirectory"
