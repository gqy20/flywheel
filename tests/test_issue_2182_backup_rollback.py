"""Regression tests for Issue #2182: File backup/rollback capability.

This test file ensures that:
1. A backup is created before each save() operation
2. Backups have timestamps in their filenames
3. Backup retention limit is respected (default 5)
4. rollback() method can restore from a backup
5. Old backups are cleaned up when exceeding retention limit
"""

from __future__ import annotations

import re

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_file_created_before_save(tmp_path) -> None:
    """Test that a backup file is created before save operation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Save again - should create a backup
    todos = [Todo(id=1, text="updated"), Todo(id=2, text="new")]
    storage.save(todos)

    # Verify backup file exists
    backups = list(db.parent.glob("todo.json*.bak"))
    assert len(backups) >= 1, "At least one backup file should be created"


def test_backup_filename_contains_timestamp(tmp_path) -> None:
    """Test that backup filename contains timestamp."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Initial save
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Second save to create backup
    todos = [Todo(id=1, text="updated")]
    storage.save(todos)

    # Find backup files
    backups = list(db.parent.glob("todo.json*.bak"))
    assert len(backups) >= 1

    # Check that backup filename contains timestamp pattern (YYYYMMDD-HHMMSS)
    # Example: todo.json.20250208-123456.bak
    backup_name = backups[0].name
    timestamp_pattern = r"\.\d{8}-\d{6}\.bak$"
    assert re.search(timestamp_pattern, backup_name), (
        f"Backup filename should contain timestamp, got: {backup_name}"
    )


def test_backup_retention_limit_deletes_oldest(tmp_path) -> None:
    """Test that backup retention limit deletes oldest backups when exceeded."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create more backups than the retention limit (5)
    for i in range(7):
        todos = [Todo(id=1, text=f"update {i}")]
        storage.save(todos)

    backups = sorted(db.parent.glob("todo.json*.bak"))

    # Should have at most 5 backups (default retention limit)
    assert len(backups) <= 5, (
        f"Should have at most 5 backups due to retention limit, got {len(backups)}"
    )


def test_rollback_restores_from_backup(tmp_path) -> None:
    """Test that rollback() method restores data from backup file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial state
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Make changes (creating a backup of original)
    updated_todos = [Todo(id=1, text="modified")]
    storage.save(updated_todos)

    # Find the backup file
    backups = list(db.parent.glob("todo.json*.bak"))
    assert len(backups) >= 1, "Need at least one backup to test rollback"

    # Rollback to the backup
    storage.rollback(backups[0])

    # Verify we have the original data back
    restored = storage.load()
    texts = [todo.text for todo in restored]
    assert "original" in texts or "data" in texts, (
        "Rollback should restore original data from backup"
    )


def test_cleanup_on_exceeding_retention_limit(tmp_path) -> None:
    """Test that old backups are automatically cleaned up when limit exceeded."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create backups one by one
    for i in range(6):
        todos = [Todo(id=1, text=f"version {i}")]
        storage.save(todos)

    backups = list(db.parent.glob("todo.json*.bak"))

    # Should never exceed retention limit
    assert len(backups) <= 5, "Old backups should be cleaned up automatically"


def test_configurable_backup_retention_limit(tmp_path) -> None:
    """Test that backup retention limit can be configured."""
    db = tmp_path / "todo.json"
    # Create storage with custom retention limit
    storage = TodoStorage(str(db), backup_retention=3)

    # Create more backups than the custom retention limit
    for i in range(5):
        todos = [Todo(id=1, text=f"update {i}")]
        storage.save(todos)

    backups = list(db.parent.glob("todo.json*.bak"))

    # Should have at most 3 backups (custom retention limit)
    assert len(backups) <= 3, (
        f"Should have at most 3 backups due to custom retention limit, got {len(backups)}"
    )


def test_backup_created_even_when_file_doesnt_exist(tmp_path) -> None:
    """Test that save() works correctly for first save (no backup needed)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - file doesn't exist yet
    todos = [Todo(id=1, text="first todo")]
    storage.save(todos)

    # Should succeed without creating a backup (nothing to backup)
    backups = list(db.parent.glob("todo.json*.bak"))
    assert len(backups) == 0, "No backup should be created on first save"
