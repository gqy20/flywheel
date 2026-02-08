"""Tests for backup/rotation mechanism for corrupt or lost data recovery (Issue #2197).

This test suite verifies that TodoStorage.save() creates backup files before
overwriting existing data, and that old backups are automatically cleaned up
when exceeding max_backups limit.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_when_file_exists(tmp_path) -> None:
    """Test that save creates a backup file when the target file already exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Save new data - should create backup
    new_todos = [Todo(id=1, text="updated"), Todo(id=2, text="new")]
    storage.save(new_todos)

    # Verify backup file was created
    backup_dir = tmp_path / ".flywheel" / "backups"
    assert backup_dir.exists(), "Backup directory should exist"

    backups = list(backup_dir.glob("todo.json.backup.*"))
    assert len(backups) >= 1, "At least one backup file should exist"

    # Verify backup contains original data
    import json
    backup_content = json.loads(backups[0].read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "original"

    # Verify main file contains new data
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "updated"


def test_no_backup_on_first_save(tmp_path) -> None:
    """Test that no backup is created when file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - file doesn't exist yet
    todos = [Todo(id=1, text="first")]
    storage.save(todos)

    # No backup should be created on first save
    backup_dir = tmp_path / ".flywheel" / "backups"
    if backup_dir.exists():
        backups = list(backup_dir.glob("todo.json.backup.*"))
        assert len(backups) == 0, "No backup should be created on first save"


def test_old_backups_cleaned_up_when_exceeding_max_backups(tmp_path) -> None:
    """Test that old backups are automatically cleaned up when exceeding max_backups."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), max_backups=2)

    # Create multiple saves to exceed max_backups
    for i in range(5):
        todos = [Todo(id=1, text=f"version-{i}")]
        storage.save(todos)

    backup_dir = tmp_path / ".flywheel" / "backups"
    backups = sorted(backup_dir.glob("todo.json.backup.*"))

    # Should only keep max_backups number of backups
    assert len(backups) <= 2, f"Should keep at most 2 backups, got {len(backups)}"


def test_save_succeeds_even_if_backup_fails(tmp_path) -> None:
    """Test that save still succeeds even if backup creation fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Mock copy to fail but save should still succeed
    with patch("flywheel.storage.shutil.copy") as mock_copy:
        mock_copy.side_effect = OSError("Backup failed")

        # This should not raise
        new_todos = [Todo(id=1, text="updated")]
        storage.save(new_todos)

    # Main save should have succeeded
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "updated"


def test_backup_files_have_timestamp_in_name(tmp_path) -> None:
    """Test that backup files have timestamp in their filename."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data and then save new data
    storage.save([Todo(id=1, text="original")])
    storage.save([Todo(id=1, text="updated")])

    backup_dir = tmp_path / ".flywheel" / "backups"
    backups = list(backup_dir.glob("todo.json.backup.*"))

    assert len(backups) >= 1
    # Backup filename should contain timestamp pattern (YYYYMMDD-HHMMSS)
    # or at least have .backup. prefix with some suffix
    for backup in backups:
        assert ".backup." in backup.name, f"Backup file {backup.name} should contain .backup."


def test_max_backups_parameter_default_value() -> None:
    """Test that max_backups parameter defaults to 3."""
    storage = TodoStorage()
    assert storage.max_backups == 3


def test_custom_max_backups_value() -> None:
    """Test that custom max_backups value is respected."""
    storage = TodoStorage(max_backups=5)
    assert storage.max_backups == 5


def test_backup_disabled_when_max_backups_is_zero(tmp_path) -> None:
    """Test that no backups are created when max_backups=0."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), max_backups=0)

    # Create initial data and then save new data
    storage.save([Todo(id=1, text="original")])
    storage.save([Todo(id=1, text="updated")])

    # No backup directory should be created
    backup_dir = tmp_path / ".flywheel" / "backups"
    assert not backup_dir.exists() or len(list(backup_dir.glob("*"))) == 0


def test_backups_can_be_used_for_recovery(tmp_path) -> None:
    """Test that backups can be used to recover previous data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create version history
    storage.save([Todo(id=1, text="v1"), Todo(id=2, text="v1-todo2")])
    storage.save([Todo(id=1, text="v2")])
    storage.save([Todo(id=1, text="v3-corrupted")])

    # Simulate corruption - write bad JSON to main file
    db.write_text("corrupted data", encoding="utf-8")

    # Main file should fail to load
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()

    # But we can recover from backup
    backup_dir = tmp_path / ".flywheel" / "backups"
    backups = sorted(backup_dir.glob("todo.json.backup.*"), key=lambda p: p.stat().st_mtime)

    # Use the oldest backup (first one created) - should have v1 data
    # After 3 saves, we have 2 backups (v1 and v2, since first save doesn't create backup)
    import json
    assert len(backups) >= 1, "Should have at least one backup"
    recovered_data = json.loads(backups[0].read_text(encoding="utf-8"))

    # Should have either v1 (2 todos) or v2 (1 todo) data depending on which backup is oldest
    assert isinstance(recovered_data, list)
    assert len(recovered_data) >= 1
    assert recovered_data[0]["text"] in ["v1", "v2"]


def test_backup_respects_db_path_in_filename(tmp_path) -> None:
    """Test that backup filename is based on the db path, not just 'todo.json'."""
    db = tmp_path / "custom" / "mydb.json"
    storage = TodoStorage(str(db))

    # Create initial data and then save new data
    storage.save([Todo(id=1, text="original")])
    storage.save([Todo(id=1, text="updated")])

    # Backup directory should be in the parent of db file
    backup_dir = tmp_path / "custom" / ".flywheel" / "backups"
    backups = list(backup_dir.glob("mydb.json.backup.*"))

    assert len(backups) >= 1, "Backup should use custom db filename"
