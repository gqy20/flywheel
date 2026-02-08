"""Tests for issue #2280: File backup/rollback capability for corrupted data recovery.

This test suite verifies that TodoStorage provides backup and restore functionality
to recover from corrupted JSON files.
"""

from __future__ import annotations

import re
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_creates_timestamped_file(tmp_path) -> None:
    """Test that backup() creates a file with .bak.YYYYMMDDHHMMSS_N suffix."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="backup test")]
    storage.save(todos)

    # Create backup
    storage.backup()

    # Verify backup file exists with correct naming pattern
    backup_files = list(db.parent.glob(".todo.json.bak.*"))
    assert len(backup_files) == 1

    backup_path = backup_files[0]
    # Check pattern: .todo.json.bak.YYYYMMDDHHMMSS_N
    pattern = r"\.todo\.json\.bak\.\d{14}_\d+$"
    assert re.match(pattern, backup_path.name)

    # Verify backup content matches original
    backup_content = backup_path.read_text(encoding="utf-8")
    assert '"text": "backup test"' in backup_content


def test_save_creates_backup_before_overwrite(tmp_path) -> None:
    """Test that save() calls backup() automatically before writing new data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original data")]
    storage.save(original_todos)

    # Modify and save - should create backup first
    modified_todos = [Todo(id=1, text="modified data")]
    storage.save(modified_todos)

    # Verify backup file was created
    backup_files = list(db.parent.glob(".todo.json.bak.*"))
    assert len(backup_files) >= 1

    # Verify backup contains original data
    latest_backup = sorted(backup_files)[-1]
    backup_content = latest_backup.read_text(encoding="utf-8")
    assert '"text": "original data"' in backup_content


def test_list_backups_returns_chronological_order(tmp_path) -> None:
    """Test that list_backups() returns backups in chronological order (oldest first)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Create multiple backups
    storage.backup()
    storage.backup()
    storage.backup()

    # Get backup list
    backups = storage.list_backups()

    # Should have 3 backups
    assert len(backups) == 3

    # Verify chronological order (oldest first)
    # Each backup should be newer than the previous
    for i in range(len(backups) - 1):
        assert backups[i].name <= backups[i + 1].name


def test_restore_from_backup(tmp_path) -> None:
    """Test that restore() successfully loads data from backup file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save original data
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Create backup
    storage.backup()
    backup_files = list(db.parent.glob(".todo.json.bak.*"))
    assert len(backup_files) == 1
    backup_path = backup_files[0]

    # Corrupt the main file
    db.write_text("{corrupted json data", encoding="utf-8")

    # Restore from backup
    storage.restore(backup_path)

    # Verify main file is restored
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "original"
    assert loaded[1].text == "data"


def test_old_backups_cleaned_up(tmp_path) -> None:
    """Test that old backups are automatically cleaned up when exceeding limit."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), max_backups=3)

    # Create initial data
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Create more backups than the limit
    for _ in range(5):
        storage.backup()

    # Should only keep max_backups (3) most recent backups
    backup_files = list(db.parent.glob(".todo.json.bak.*"))
    assert len(backup_files) == 3


def test_backup_when_file_doesnt_exist(tmp_path) -> None:
    """Test that backup() is a no-op when the original file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # File doesn't exist yet - backup should be a no-op
    storage.backup()

    # No backup files should be created
    backup_files = list(db.parent.glob(".todo.json.bak.*"))
    assert len(backup_files) == 0


def test_multiple_backups_kept_within_limit(tmp_path) -> None:
    """Test that exactly max_backups backups are retained."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), max_backups=5)

    # Create initial data
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Create exactly 5 backups
    for _ in range(5):
        storage.backup()

    # Should keep all 5 backups
    backup_files = list(db.parent.glob(".todo.json.bak.*"))
    assert len(backup_files) == 5

    # Create one more backup
    storage.backup()

    # Should still only have 5 (oldest removed)
    backup_files = list(db.parent.glob(".todo.json.bak.*"))
    assert len(backup_files) == 5


def test_restore_uses_atomic_replace(tmp_path) -> None:
    """Test that restore() uses atomic os.replace for safety."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data and backup
    todos = [Todo(id=1, text="test")]
    storage.save(todos)
    storage.backup()
    backup_files = list(db.parent.glob(".todo.json.bak.*"))

    # Mock os.replace to verify it's called
    with patch("flywheel.storage.os.replace") as mock_replace:
        storage.restore(backup_files[0])
        mock_replace.assert_called_once()

    # Verify restore succeeded
    loaded = storage.load()
    assert len(loaded) == 1
