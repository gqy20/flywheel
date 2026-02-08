"""Tests for backup/rollback capability (Issue #2280).

These tests verify that:
1. backup() creates timestamped backup file before save
2. Backups use same atomic write pattern as main save
3. save() calls backup() automatically before overwriting
4. list_backups() returns list of available backup files with timestamps
5. restore() restores from specific backup
6. Only last N backups retained (default 5)
7. Old backups are automatically cleaned up
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_creates_timestamped_file(tmp_path) -> None:
    """Test that backup() creates a file with .bak.YYYYMMDDHHMMSS suffix."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="initial task")]
    storage.save(todos)

    # Call backup explicitly
    storage.backup()

    # Verify backup file was created with .bak. prefix and timestamp suffix
    backup_files = list(db.parent.glob(f"{db.name}.bak.*"))
    assert len(backup_files) == 1, "Should create exactly one backup file"

    backup_file = backup_files[0]
    # Verify timestamp format: .bak.YYYYMMDDHHMMSS
    assert re.match(rf"^{re.escape(db.name)}\.bak\.\d{{14}}$", backup_file.name)

    # Verify backup contains the same data
    with open(backup_file, encoding="utf-8") as f:
        backup_data = json.load(f)
    assert len(backup_data) == 1
    assert backup_data[0]["text"] == "initial task"


def test_save_creates_backup_before_writing(tmp_path) -> None:
    """Test that save() creates a backup before writing new data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Save new data (should create backup first)
    new_todos = [Todo(id=1, text="modified task", done=True)]
    storage.save(new_todos)

    # Verify backup was created
    backup_files = list(db.parent.glob(f"{db.name}.bak.*"))
    assert len(backup_files) >= 1, "Should create at least one backup"

    # Verify backup contains original data
    with open(backup_files[-1], encoding="utf-8") as f:
        backup_data = json.load(f)
    assert len(backup_data) == 1
    assert backup_data[0]["text"] == "original task"
    assert backup_data[0]["done"] is False

    # Verify main file has new data
    current = storage.load()
    assert len(current) == 1
    assert current[0].text == "modified task"
    assert current[0].done is True


def test_list_backups_returns_chronologically_ordered_list(tmp_path) -> None:
    """Test that list_backups() returns chronologically ordered backup list."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="task1")]
    storage.save(todos)

    # Mock datetime to return incrementing timestamps
    with patch("flywheel.storage.datetime") as mock_datetime:
        # Create a base datetime and setup the mock
        base_dt = datetime(2025, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = base_dt
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        # Create multiple backups with mocked timestamps
        storage.backup()
        mock_datetime.now.return_value = datetime(2025, 1, 1, 12, 0, 1)
        storage.backup()
        mock_datetime.now.return_value = datetime(2025, 1, 1, 12, 0, 2)
        storage.backup()

    # Get list of backups
    backups = storage.list_backups()

    # Should have 3 backups
    assert len(backups) == 3

    # Verify chronological order (oldest first)
    timestamps = [b["timestamp"] for b in backups]
    assert timestamps == sorted(timestamps), "Backups should be in chronological order"

    # Verify each backup has required fields
    for backup in backups:
        assert "path" in backup
        assert "timestamp" in backup
        assert isinstance(backup["path"], Path)


def test_restore_loads_from_backup_file(tmp_path) -> None:
    """Test that restore() successfully loads data from backup file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data and save
    original_todos = [
        Todo(id=1, text="task1"),
        Todo(id=2, text="task2", done=True),
    ]
    storage.save(original_todos)
    storage.backup()

    # Modify main file
    modified_todos = [Todo(id=1, text="corrupted data")]
    storage.save(modified_todos)

    # Get backup list and restore from first backup
    backups = storage.list_backups()
    assert len(backups) == 1

    storage.restore(backups[0]["path"])

    # Verify main file now contains original data
    restored = storage.load()
    assert len(restored) == 2
    assert restored[0].text == "task1"
    assert restored[1].text == "task2"
    assert restored[1].done is True


def test_old_backups_cleaned_up_when_exceeding_limit(tmp_path) -> None:
    """Test that old backups are automatically cleaned up when exceeding limit."""
    db = tmp_path / "todo.json"

    # Create storage with limit of 3 backups
    limited_storage = TodoStorage(str(db), max_backups=3)

    # Create initial data
    todos = [Todo(id=1, text="task")]
    limited_storage.save(todos)

    # Create 5 backups (should only keep last 3)
    with patch("flywheel.storage.datetime") as mock_datetime:
        base_dt = datetime(2025, 1, 1, 12, 0, 0)
        for i in range(5):
            mock_datetime.now.return_value = base_dt + timedelta(seconds=i)
            limited_storage.save([Todo(id=1, text=f"task-{i}")])

    backups = limited_storage.list_backups()
    # Should only have 3 backups (the most recent ones)
    assert len(backups) == 3, "Should only retain max_backups"


def test_backup_works_when_original_file_doesnt_exist(tmp_path) -> None:
    """Test that backup works correctly even when original file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), max_backups=3)

    # Don't create initial file - call backup directly
    # Should not crash or create backup if file doesn't exist
    storage.backup()

    # No backup should be created since original file doesn't exist
    backup_files = list(db.parent.glob(f"{db.name}.bak.*"))
    assert len(backup_files) == 0, "Should not create backup when file doesn't exist"


def test_backup_uses_atomic_write_pattern(tmp_path) -> None:
    """Test that backups use the same atomic write pattern as main save."""
    import tempfile
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Track that tempfile.mkstemp is used for backup creation
    original_mkstemp = tempfile.mkstemp
    call_count = [0]

    def tracking_mkstemp(*args, **kwargs):
        call_count[0] += 1
        return original_mkstemp(*args, **kwargs)

    with patch("flywheel.storage.tempfile.mkstemp", side_effect=tracking_mkstemp):
        storage.backup()

        # Verify mkstemp was called (atomic write pattern)
        assert call_count[0] > 0, "Backup should use atomic write pattern (tempfile.mkstemp)"


def test_multiple_saves_create_multiple_backups(tmp_path) -> None:
    """Test that multiple save operations create multiple backups up to the limit."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), max_backups=5)

    # Create multiple saves with mocked timestamps
    with patch("flywheel.storage.datetime") as mock_datetime:
        base_dt = datetime(2025, 1, 1, 12, 0, 0)
        for i in range(3):
            mock_datetime.now.return_value = base_dt + timedelta(seconds=i)
            storage.save([Todo(id=1, text=f"version-{i}")])

    backups = storage.list_backups()
    # Should have 2 backups (first save creates file, subsequent saves create backups)
    # First save creates the initial file, second save creates backup of initial, third creates backup of second
    assert len(backups) == 2


def test_default_max_backups_is_five(tmp_path) -> None:
    """Test that default max_backups value is 5."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    assert storage.max_backups == 5, "Default max_backups should be 5"


def test_restore_from_nonexistent_backup_raises_error(tmp_path) -> None:
    """Test that restoring from a non-existent backup raises an appropriate error."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Try to restore from non-existent backup
    fake_backup = tmp_path / "nonexistent.bak.20250101120000"

    with pytest.raises((FileNotFoundError, ValueError)):
        storage.restore(fake_backup)


def test_list_backups_empty_when_no_backups(tmp_path) -> None:
    """Test that list_backups() returns empty list when no backups exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    backups = storage.list_backups()
    assert backups == []
