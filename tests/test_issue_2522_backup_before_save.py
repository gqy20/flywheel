"""Regression test for issue #2522: File backup before save operations.

This test suite verifies that TodoStorage.save() creates backups before
overwriting the target file, providing recovery options if corrupted data
is written.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_created_on_save_when_file_exists(tmp_path) -> None:
    """Test that a backup is created on save when target file exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Save new data - should create backup
    new_todos = [Todo(id=2, text="new task")]
    storage.save(new_todos)

    # Verify backup was created with timestamp
    backup_files = list(db.parent.glob(".todo.json.bak.*"))
    assert len(backup_files) == 1, f"Expected 1 backup file, found {len(backup_files)}"

    # Verify backup name pattern
    backup = backup_files[0]
    assert backup.name.startswith(".todo.json.bak.")
    # Verify timestamp format (YYYYMMDDHHMMSS)
    timestamp_match = re.search(r"\.(\d{14})$", backup.name)
    assert timestamp_match is not None, f"Backup should have timestamp suffix, got {backup.name}"


def test_old_backups_rotated_when_limit_exceeded(tmp_path) -> None:
    """Test that only N most recent backups are kept."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_limit=3)

    # Create initial data
    storage.save([Todo(id=1, text="initial")])

    # Create more saves than the limit
    for i in range(5):
        storage.save([Todo(id=i + 2, text=f"task {i}")])

    # Verify only backup_limit backups exist
    backup_files = sorted(db.parent.glob(".todo.json.bak.*"))
    assert len(backup_files) == 3, (
        f"Expected 3 backup files, found {len(backup_files)}: {backup_files}"
    )


def test_list_backups_returns_available_backups(tmp_path) -> None:
    """Test that list_backups returns all backup files."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data and multiple saves
    storage.save([Todo(id=1, text="first")])
    storage.save([Todo(id=2, text="second")])
    storage.save([Todo(id=3, text="third")])

    # List backups
    backups = storage.list_backups()

    # Should have 2 backups (after first and second saves)
    assert len(backups) == 2, f"Expected 2 backups, found {len(backups)}"

    # Verify all are Path objects pointing to valid files
    for backup in backups:
        assert isinstance(backup, Path)
        assert backup.exists()


def test_restore_from_backup_correctly_restores_data(tmp_path) -> None:
    """Test that restore from backup correctly restores data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create original data
    original_todos = [
        Todo(id=1, text="task 1"),
        Todo(id=2, text="task 2", done=True),
    ]
    storage.save(original_todos)

    # Overwrite with new data
    storage.save([Todo(id=3, text="different task")])

    # Get the backup file
    backups = storage.list_backups()
    assert len(backups) == 1

    # Restore from backup
    storage.restore(backups[0])

    # Verify original data was restored
    restored = storage.load()
    assert len(restored) == 2
    assert restored[0].text == "task 1"
    assert restored[1].text == "task 2"
    assert restored[1].done is True


def test_backup_can_be_disabled(tmp_path) -> None:
    """Test that backup feature can be disabled."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backup=False)

    # Create initial data
    storage.save([Todo(id=1, text="initial")])

    # Save again - should NOT create backup
    storage.save([Todo(id=2, text="new")])

    # Verify no backup files exist
    backup_files = list(db.parent.glob(".todo.json.bak.*"))
    assert len(backup_files) == 0, f"Expected 0 backup files, found {len(backup_files)}"


def test_backup_not_created_on_first_save(tmp_path) -> None:
    """Test that no backup is created when file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no existing file to backup
    storage.save([Todo(id=1, text="first")])

    # Verify no backup files exist
    backup_files = list(db.parent.glob(".todo.json.bak.*"))
    assert len(backup_files) == 0, f"Expected 0 backup files, found {len(backup_files)}"


def test_default_backup_limit_is_three(tmp_path) -> None:
    """Test that default backup limit is 3 if not specified."""
    db = tmp_path / "todo.json"

    # Create with default settings
    storage = TodoStorage(str(db))

    # Check default limit
    assert storage._backup_limit == 3


def test_list_backups_returns_empty_list_when_no_backups(tmp_path) -> None:
    """Test that list_backups returns empty list when no backups exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # No saves yet, no backups
    backups = storage.list_backups()
    assert backups == []


def test_restore_from_nonexistent_backup_raises_error(tmp_path) -> None:
    """Test that restoring from non-existent backup raises appropriate error."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Try to restore from non-existent backup
    fake_backup = tmp_path / ".todo.json.bak.20250209"

    with pytest.raises(FileNotFoundError):
        storage.restore(fake_backup)
