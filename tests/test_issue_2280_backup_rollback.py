"""Tests for file backup/rollback capability (Issue #2280).

This test suite verifies that:
1. TodoStorage.backup() creates timestamped backup files
2. TodoStorage.save() calls backup() automatically before overwriting
3. TodoStorage.list_backups() returns available backup files with timestamps
4. TodoStorage.restore() can restore from specific backup
5. Only last N backups are retained (configurable, default 5)
6. Old backups are automatically cleaned up
7. Backup works correctly when original file doesn't exist yet
"""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def _get_backup_files(path: Path) -> list[Path]:
    """Helper to get all backup files for a given path."""
    return sorted(path.parent.glob(f"{path.name}.bak.*"))


def test_backup_creates_timestamped_file(tmp_path) -> None:
    """Test that backup() creates file with .bak.YYYYMMDDHHMMSS suffix."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    todos = [Todo(id=1, text="original task"), Todo(id=2, text="another task")]
    storage.save(todos)

    # Call backup explicitly
    storage.backup()

    # Verify backup file was created with correct suffix pattern
    backup_files = _get_backup_files(db)
    assert len(backup_files) == 1

    backup_name = backup_files[0].name
    assert backup_name.startswith("todo.json.bak.")
    # Verify timestamp format: YYYYMMDDHHMMSS + 6 digit microseconds
    timestamp = backup_name.replace("todo.json.bak.", "")
    assert re.match(r"^\d{20}$", timestamp), f"Invalid timestamp format: {timestamp}"

    # Verify backup contains original data
    backup_storage = TodoStorage(str(backup_files[0]))
    backed_up_todos = backup_storage.load()
    assert len(backed_up_todos) == 2
    assert backed_up_todos[0].text == "original task"
    assert backed_up_todos[1].text == "another task"


def test_save_creates_backup_before_overwriting(tmp_path) -> None:
    """Test that save() creates backup before writing new data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Modify todos and save again
    modified_todos = [Todo(id=1, text="modified"), Todo(id=2, text="new")]
    storage.save(modified_todos)

    # Verify backup was created
    backup_files = _get_backup_files(db)
    assert len(backup_files) == 1

    # Verify backup contains original data
    backup_storage = TodoStorage(str(backup_files[0]))
    backed_up_todos = backup_storage.load()
    assert len(backed_up_todos) == 1
    assert backed_up_todos[0].text == "original"


def test_save_no_backup_when_file_doesnt_exist(tmp_path) -> None:
    """Test that backup works correctly even when original file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save when file doesn't exist - should not create backup
    todos = [Todo(id=1, text="first todo")]
    storage.save(todos)

    # Verify no backup was created
    backup_files = _get_backup_files(db)
    assert len(backup_files) == 0

    # Verify main file was created
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "first todo"


def test_list_backups_returns_chronologically_ordered_list(tmp_path) -> None:
    """Test that list_backups() returns chronologically ordered backup list."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    todos = [Todo(id=1, text="task")]
    storage.save(todos)

    # Create multiple backups with different timestamps
    for i in range(3):
        storage.save([Todo(id=1, text=f"version {i}")])
        time.sleep(0.1)  # Ensure different timestamps

    # Get list of backups
    backups = storage.list_backups()

    # Should have 3 backups
    assert len(backups) == 3

    # Verify they're ordered chronologically (oldest first)
    for i in range(len(backups) - 1):
        assert backups[i]["timestamp"] <= backups[i + 1]["timestamp"]

    # Verify each backup has required fields
    for backup in backups:
        assert "path" in backup
        assert "timestamp" in backup
        assert isinstance(backup["path"], str)
        assert isinstance(backup["timestamp"], datetime)


def test_restore_loads_data_from_backup(tmp_path) -> None:
    """Test that restore() successfully loads data from backup file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create todos and backup
    original_todos = [Todo(id=1, text="backup test"), Todo(id=2, text="data")]
    storage.save(original_todos)
    storage.backup()

    # Modify current data
    storage.save([Todo(id=1, text="corrupted data")])

    # Get backup list and restore from first backup
    backups = storage.list_backups()
    assert len(backups) > 0

    restored_todos = storage.restore(Path(backups[0]["path"]))

    # Verify restored data matches original
    assert len(restored_todos) == 2
    assert restored_todos[0].text == "backup test"
    assert restored_todos[1].text == "data"


def test_old_backups_cleaned_up_when_exceeding_limit(tmp_path) -> None:
    """Test that old backups are cleaned up when exceeding limit."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    todos = [Todo(id=1, text="task")]
    storage.save(todos)

    # Create more backups than the default limit (5)
    for i in range(7):
        storage.save([Todo(id=1, text=f"version {i}")])
        time.sleep(0.1)  # Ensure different timestamps

    # Verify only last 5 backups are retained
    backups = storage.list_backups()
    assert len(backups) == 5

    # Verify the files on disk match
    backup_files = _get_backup_files(db)
    assert len(backup_files) == 5


def test_backup_limit_is_configurable(tmp_path) -> None:
    """Test that backup limit can be configured."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_limit=3)

    # Create initial todos
    todos = [Todo(id=1, text="task")]
    storage.save(todos)

    # Create 5 backups
    for i in range(5):
        storage.save([Todo(id=1, text=f"version {i}")])
        time.sleep(0.1)  # Ensure different timestamps

    # Verify only last 3 backups are retained
    backups = storage.list_backups()
    assert len(backups) == 3


def test_backup_uses_atomic_write_pattern(tmp_path) -> None:
    """Test that backup uses same atomic write pattern as main save."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Mock os.replace to track if it was called for backup
    with patch("flywheel.storage.os.replace") as mock_replace:
        storage.backup()
        # Verify atomic replace was used for backup
        assert mock_replace.call_count >= 1


def test_restore_raises_error_for_nonexistent_backup(tmp_path) -> None:
    """Test that restore() raises error for nonexistent backup file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Try to restore from nonexistent file
    with pytest.raises(FileNotFoundError):
        storage.restore(Path(tmp_path / "nonexistent.bak.20250208120000"))


def test_backup_timestamp_is_correct(tmp_path) -> None:
    """Test that backup timestamp in filename matches actual backup time."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    todos = [Todo(id=1, text="test")]
    storage.save(todos)

    # Get time before backup
    before = datetime.now(UTC)

    # Create backup
    storage.backup()

    # Get time after backup
    after = datetime.now(UTC)

    # Get backup info and verify timestamp
    backups = storage.list_backups()
    assert len(backups) == 1

    backup_time = backups[0]["timestamp"]
    # Truncate to seconds for comparison (backup has microsecond precision)
    before_seconds = before.replace(microsecond=0)
    after_seconds = after.replace(microsecond=0)
    backup_seconds = backup_time.replace(microsecond=0)

    assert before_seconds <= backup_seconds <= after_seconds


def test_multiple_saves_create_multiple_backups(tmp_path) -> None:
    """Test that multiple saves create multiple backups up to the limit."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no backup (file doesn't exist)
    storage.save([Todo(id=1, text="initial")])
    assert len(_get_backup_files(db)) == 0

    # Second save - creates 1 backup
    storage.save([Todo(id=1, text="second")])
    assert len(_get_backup_files(db)) == 1

    # Third save - creates 2nd backup
    time.sleep(0.1)  # Ensure different timestamps
    storage.save([Todo(id=1, text="third")])
    assert len(_get_backup_files(db)) == 2

    # Fourth save - creates 3rd backup
    time.sleep(0.1)  # Ensure different timestamps
    storage.save([Todo(id=1, text="fourth")])
    assert len(_get_backup_files(db)) == 3


def test_list_backups_returns_empty_list_when_no_backups(tmp_path) -> None:
    """Test that list_backups() returns empty list when no backups exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # No backups yet
    backups = storage.list_backups()
    assert backups == []


def test_backup_with_corrupted_main_file(tmp_path) -> None:
    """Test that backup can be used to recover from corrupted main file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create valid todos and backup
    original_todos = [Todo(id=1, text="important"), Todo(id=2, text="data")]
    storage.save(original_todos)
    storage.backup()

    # Corrupt the main file
    db.write_text("{invalid json content", encoding="utf-8")

    # Verify main file is corrupted
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()

    # Restore from backup
    backups = storage.list_backups()
    restored_todos = storage.restore(Path(backups[0]["path"]))

    # Verify data was recovered
    assert len(restored_todos) == 2
    assert restored_todos[0].text == "important"
    assert restored_todos[1].text == "data"
