"""Tests for backup and rollback capability in TodoStorage.

This test suite verifies that TodoStorage creates backups before save operations
and can rollback from backup files.
"""

from __future__ import annotations

import re

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_file_created_before_save(tmp_path) -> None:
    """Test that a backup file is created with timestamp before each save."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data (no backup on first save since file doesn't exist)
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Second save should create a backup
    todos = [Todo(id=1, text="updated")]
    storage.save(todos)

    # Verify backup file was created
    backups = list(db.parent.glob(".todo.json.*.bak"))
    assert len(backups) >= 1, "At least one backup file should be created"

    # Backup filename should contain timestamp
    assert re.search(r"\d{14}", backups[0].name), "Backup filename should contain timestamp"


def test_backup_retention_limit_deletes_oldest(tmp_path) -> None:
    """Test that backup retention limit deletes oldest backups when exceeded."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create multiple saves to exceed retention limit (default 5)
    for i in range(7):
        todos = [Todo(id=i, text=f"todo-{i}")]
        storage.save(todos)

    # Count backup files
    backups = sorted(db.parent.glob(".todo.json.*.bak"))
    assert len(backups) <= 5, f"Should have at most 5 backups, got {len(backups)}"


def test_rollback_restores_from_backup(tmp_path) -> None:
    """Test that rollback method restores from a backup file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Save new data (overwriting original - this creates a backup)
    new_todos = [Todo(id=3, text="new")]
    storage.save(new_todos)

    # Get the backup file
    backups = list(db.parent.glob(".todo.json.*.bak"))
    assert len(backups) >= 1, "Should have at least one backup"

    # Verify current state has new data
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "new"

    # Rollback to backup
    storage.rollback(backups[0])

    # Verify original data is restored
    restored = storage.load()
    assert len(restored) == 2
    assert restored[0].text == "original"
    assert restored[1].text == "data"


def test_cleanup_on_exceeding_retention_limit(tmp_path) -> None:
    """Test that oldest backups are automatically cleaned up when exceeding retention limit."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_retention=3)

    # Create saves to exceed retention limit
    for i in range(5):
        todos = [Todo(id=i, text=f"todo-{i}")]
        storage.save(todos)

    # Count backup files - should be at most retention limit
    backups = list(db.parent.glob(".todo.json.*.bak"))
    assert len(backups) <= 3, f"Should have at most 3 backups (retention limit), got {len(backups)}"


def test_no_error_when_rolling_back_nonexistent_storage(tmp_path) -> None:
    """Test that rollback on a storage that hasn't been saved yet handles gracefully."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a fake backup file manually
    backup_path = db.parent / ".todo.json.20250208120000.bak"
    backup_content = '[{"id": 1, "text": "backup", "done": false}]'
    backup_path.write_text(backup_content, encoding="utf-8")

    # Rollback should work even if main file doesn't exist
    storage.rollback(backup_path)

    # Verify data was restored
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "backup"


def test_custom_backup_retention_limit(tmp_path) -> None:
    """Test that custom backup retention limit is respected."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_retention=2)

    # Create more saves than retention limit
    for i in range(4):
        todos = [Todo(id=i, text=f"todo-{i}")]
        storage.save(todos)

    # Should have at most 2 backups
    backups = list(db.parent.glob(".todo.json.*.bak"))
    assert len(backups) <= 2


def test_backup_disabled_with_zero_retention(tmp_path) -> None:
    """Test that setting backup_retention to 0 disables backups."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_retention=0)

    # Create saves
    for i in range(3):
        todos = [Todo(id=i, text=f"todo-{i}")]
        storage.save(todos)

    # Should have no backup files
    backups = list(db.parent.glob(".todo.json.*.bak"))
    assert len(backups) == 0, "Should have no backups when retention is 0"
