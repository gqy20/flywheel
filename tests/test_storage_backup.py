"""Tests for automatic backup creation before file modifications.

This test suite verifies that TodoStorage creates backups before overwriting
files, providing recovery from data corruption or accidental changes.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_created_on_save(tmp_path, monkeypatch) -> None:
    """Test that saving creates a .bak file when target exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Save again - should create backup
    new_todos = [Todo(id=1, text="modified", done=True)]
    storage.save(new_todos)

    # Verify backup file exists
    backup_files = list(tmp_path.glob("todo.json.*.bak"))
    assert len(backup_files) >= 1, "Backup file should be created"

    # Verify backup contains original data
    backup_content = backup_files[0].read_text(encoding="utf-8")
    backup_data = json.loads(backup_content)
    assert len(backup_data) == 1
    assert backup_data[0]["text"] == "original"
    assert backup_data[0]["done"] is False


def test_no_backup_on_first_save(tmp_path) -> None:
    """Test that no backup is created when file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - file doesn't exist, no backup should be created
    todos = [Todo(id=1, text="first save")]
    storage.save(todos)

    # Verify no backup files exist
    backup_files = list(tmp_path.glob("todo.json.*.bak"))
    assert len(backup_files) == 0, "No backup should be created on first save"


def test_backup_rotation_default(tmp_path, monkeypatch) -> None:
    """Test that default rotation keeps 3 backups."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Ensure default backup count
    monkeypatch.delenv("FLYWHEEL_BACKUP_COUNT", raising=False)

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Make 5 saves to test rotation (should keep only 3 backups)
    for i in range(1, 6):
        storage.save([Todo(id=1, text=f"version-{i}")])

    # Count backup files
    backup_files = sorted(tmp_path.glob("todo.json.*.bak"))
    assert len(backup_files) <= 3, f"Should keep at most 3 backups, got {len(backup_files)}"


def test_backup_rotation_custom(tmp_path, monkeypatch) -> None:
    """Test that FLYWHEEL_BACKUP_COUNT env var controls backup count."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Set custom backup count
    monkeypatch.setenv("FLYWHEEL_BACKUP_COUNT", "2")

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Make 5 saves
    for i in range(1, 6):
        storage.save([Todo(id=1, text=f"version-{i}")])

    # Count backup files
    backup_files = sorted(tmp_path.glob("todo.json.*.bak"))
    assert len(backup_files) <= 2, f"Should keep at most 2 backups, got {len(backup_files)}"


def test_restore_from_backup(tmp_path) -> None:
    """Test that restore_from_backup() method restores from backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save original data
    original_todos = [Todo(id=1, text="backup data"), Todo(id=2, text="to restore")]
    storage.save(original_todos)

    # Save new data (creates backup)
    storage.save([Todo(id=3, text="corrupted data")])

    # Corrupt the main file
    db.write_text("{invalid json", encoding="utf-8")

    # Restore from backup
    storage.restore_from_backup()

    # Verify original data was restored
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "backup data"
    assert loaded[1].text == "to restore"


def test_restore_from_backup_raises_when_no_backup(tmp_path) -> None:
    """Test that restore_from_backup() raises error when no backup exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # No save = no backup
    with pytest.raises(FileNotFoundError, match="No backup file found"):
        storage.restore_from_backup()


def test_backup_has_valid_json(tmp_path) -> None:
    """Test that backup files contain valid parseable JSON."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create data with special characters
    original_todos = [
        Todo(id=1, text="unicode: 你好"),
        Todo(id=2, text='quotes: "test"', done=True),
        Todo(id=3, text="newlines\nand\ttabs"),
    ]
    storage.save(original_todos)

    # Save new data to create backup
    storage.save([Todo(id=4, text="new")])

    # Get backup file
    backup_files = list(tmp_path.glob("todo.json.*.bak"))
    assert len(backup_files) == 1

    # Verify backup has valid JSON
    backup_content = backup_files[0].read_text(encoding="utf-8")
    backup_data = json.loads(backup_content)

    assert len(backup_data) == 3
    assert backup_data[0]["text"] == "unicode: 你好"
    assert backup_data[1]["text"] == 'quotes: "test"'
    assert backup_data[1]["done"] is True


def test_backup_with_zero_count_disables_backups(tmp_path, monkeypatch) -> None:
    """Test that FLYWHEEL_BACKUP_COUNT=0 disables backups."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Disable backups
    monkeypatch.setenv("FLYWHEEL_BACKUP_COUNT", "0")

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Save again
    storage.save([Todo(id=1, text="modified")])

    # Verify no backup files created
    backup_files = list(tmp_path.glob("todo.json.*.bak"))
    assert len(backup_files) == 0, "No backups should be created when count is 0"
