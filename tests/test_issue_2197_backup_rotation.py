"""Tests for backup/rotation mechanism in TodoStorage.

This test suite verifies that TodoStorage creates backup files before
overwriting existing data, providing recovery from corruption or data loss.
Regression test for issue #2197.
"""

from __future__ import annotations

import json
import re
import time
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_before_overwrite(tmp_path) -> None:
    """Test that save creates a backup copy when overwriting existing file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Save new data - should create backup
    new_todos = [Todo(id=1, text="updated task")]
    storage.save(new_todos)

    # Verify backup file was created
    parent = db.parent
    backup_files = list(parent.glob(f".{db.name}.*.bak"))

    assert len(backup_files) >= 1, "Backup file should be created"

    # Verify backup contains original data
    backup_content = backup_files[0].read_text(encoding="utf-8")
    backup_todos = json.loads(backup_content)
    assert len(backup_todos) == 1
    assert backup_todos[0]["text"] == "original task"


def test_old_backups_cleaned_when_exceeding_max_backups(tmp_path) -> None:
    """Test that old backups are removed when max_backups is exceeded."""
    db = tmp_path / "todo.json"

    # Create storage with max_backups=2
    storage = TodoStorage(str(db), enable_backups=True, max_backups=2)

    # First save
    storage.save([Todo(id=1, text="version 1")])
    time.sleep(0.01)  # Ensure different timestamps
    # Second save - creates first backup
    storage.save([Todo(id=1, text="version 2")])
    time.sleep(0.01)  # Ensure different timestamps
    # Third save - creates second backup, should clean first backup
    storage.save([Todo(id=1, text="version 3")])
    time.sleep(0.01)  # Ensure different timestamps
    # Fourth save - creates third backup, should clean second backup
    storage.save([Todo(id=1, text="version 4")])

    # Verify only max_backups (2) backups exist
    parent = db.parent
    # Sort by timestamp in filename for consistent ordering
    # Filename pattern: .todo.json.<timestamp>.bak
    backup_files = sorted(
        parent.glob(f".{db.name}.*.bak"),
        key=lambda p: int(p.name.split(".")[-2]),
    )

    assert len(backup_files) == 2, "Should only keep max_backups backup files"

    # The 2 most recent backups should be for version 3 and version 4
    # (version 2 was cleaned since we only keep max_backups=2)
    content1 = json.loads(backup_files[0].read_text(encoding="utf-8"))
    content2 = json.loads(backup_files[1].read_text(encoding="utf-8"))

    # The older of the two remaining should be version 2, newer is version 3
    # (because we keep 2 backups: the last 2 versions before the current one)
    assert content1[0]["text"] in ["version 2", "version 3"]
    assert content2[0]["text"] in ["version 2", "version 3"]


def test_save_succeeds_even_if_backup_creation_fails(tmp_path) -> None:
    """Test that save still succeeds even if backup creation fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    # Create initial data
    storage.save([Todo(id=1, text="original")])

    # Mock shutil.copy to fail but let main save proceed
    def failing_copy(*args, **kwargs):
        raise OSError("Backup creation failed")

    import shutil

    with patch.object(shutil, "copy", failing_copy):
        # This should NOT raise - main save should succeed
        storage.save([Todo(id=1, text="new data")])

    # Verify main file was updated despite backup failure
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "new data"


def test_backups_disabled_by_default(tmp_path) -> None:
    """Test that backup creation is disabled by default."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save multiple times
    storage.save([Todo(id=1, text="version 1")])
    storage.save([Todo(id=1, text="version 2")])
    storage.save([Todo(id=1, text="version 3")])

    # Verify NO backup files were created
    parent = db.parent
    backup_files = list(parent.glob(f".{db.name}.*.bak"))

    assert len(backup_files) == 0, "No backups should be created when disabled"


def test_backup_enabled_with_flag(tmp_path) -> None:
    """Test that backups are created when enable_backups=True."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    # Save twice to create a backup
    storage.save([Todo(id=1, text="version 1")])
    storage.save([Todo(id=1, text="version 2")])

    # Verify backup file was created
    parent = db.parent
    backup_files = list(parent.glob(f".{db.name}.*.bak"))

    assert len(backup_files) >= 1, "Backup should be created when enabled"


def test_no_backup_on_first_save(tmp_path) -> None:
    """Test that no backup is created when file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    # First save - file doesn't exist, so no backup should be created
    storage.save([Todo(id=1, text="first save")])

    # Verify no backup files
    parent = db.parent
    backup_files = list(parent.glob(f".{db.name}.*.bak"))

    assert len(backup_files) == 0, "No backup on first save (no existing file)"


def test_backup_naming_includes_timestamp(tmp_path) -> None:
    """Test that backup files include timestamp in their name."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True)

    # Create initial data
    storage.save([Todo(id=1, text="original")])

    # Save to create backup
    storage.save([Todo(id=1, text="updated")])

    # Verify backup file naming pattern: .todo.json.<timestamp>.bak
    parent = db.parent
    backup_files = list(parent.glob(f".{db.name}.*.bak"))

    assert len(backup_files) >= 1
    # Check that filename matches expected pattern
    assert re.match(rf"\.{re.escape(db.name)}\.\d+\.bak", backup_files[0].name)


def test_backups_can_be_used_for_recovery(tmp_path) -> None:
    """Test that backup files can be used to recover lost data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=True, max_backups=3)

    # Create a history of versions
    versions = [
        [Todo(id=1, text="important task v1")],
        [Todo(id=1, text="important task v2"), Todo(id=2, text="added task")],
        [Todo(id=1, text="important task v3"), Todo(id=2, text="added task")],
    ]

    for todos in versions:
        storage.save(todos)

    # Simulate corruption: write invalid JSON to main file
    db.write_text("corrupted data { invalid", encoding="utf-8")

    # Verify main file is corrupted
    with pytest.raises(ValueError, match="Invalid JSON"):
        storage.load()

    # But we can recover from backup
    parent = db.parent
    backup_files = sorted(parent.glob(f".{db.name}.*.bak"))

    assert len(backup_files) >= 1

    # Use most recent backup to recover
    most_recent_backup = backup_files[-1]
    backup_content = most_recent_backup.read_text(encoding="utf-8")
    recovered_todos = json.loads(backup_content)

    # Verify we recovered valid data
    assert len(recovered_todos) == 2
    assert recovered_todos[0]["text"] == "important task v2"
    assert recovered_todos[1]["text"] == "added task"
