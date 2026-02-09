"""Tests for file backup rotation feature in TodoStorage.

Issue #2522: Add file backup before save operations

This test suite verifies that:
1. Backups are created before save() when file exists
2. Old backups are rotated/removed when limit exceeded
3. list_backups() returns available backup files
4. restore() can restore from a specific backup
5. Backup feature can be disabled
"""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def _extract_timestamp_from_backup(backup_path: Path) -> datetime:
    """Extract timestamp from backup filename like .todo.json.bak.20250209143000."""
    match = re.search(r"\.bak\.(\d{14})(?:_\d+)?$", backup_path.name)
    if not match:
        raise ValueError(f"No timestamp found in backup path: {backup_path}")
    return datetime.strptime(match.group(1), "%Y%m%d%H%M%S").replace(tzinfo=UTC)


def test_backup_created_on_save_when_file_exists(tmp_path) -> None:
    """Test that backup is created on save when target file exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos
    initial_todos = [Todo(id=1, text="original task")]
    storage.save(initial_todos)

    # Modify and save again - should create backup
    updated_todos = [Todo(id=1, text="updated task")]
    storage.save(updated_todos)

    # Verify backup was created
    backups = storage.list_backups()
    assert len(backups) == 1
    assert backups[0].name.startswith(".todo.json.bak.")

    # Verify backup contains original data
    backup_content = backups[0].read_text(encoding="utf-8")
    assert '"original task"' in backup_content


def test_no_backup_created_on_first_save(tmp_path) -> None:
    """Test that no backup is created when file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no existing file
    todos = [Todo(id=1, text="first task")]
    storage.save(todos)

    # No backups should exist
    backups = storage.list_backups()
    assert len(backups) == 0


def test_backup_rotation_keeps_only_configured_limit(tmp_path) -> None:
    """Test that old backups are removed when limit is exceeded."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_limit=3)

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Save multiple times to create backups
    for i in range(5):
        storage.save([Todo(id=1, text=f"version {i}")])
        time.sleep(0.01)  # Ensure different timestamps

    # Should only keep 3 most recent backups
    backups = storage.list_backups()
    assert len(backups) == 3

    # Verify backups are ordered newest to oldest
    timestamps = [_extract_timestamp_from_backup(b) for b in backups]
    assert timestamps == sorted(timestamps, reverse=True)


def test_backup_limit_zero_disables_backups(tmp_path) -> None:
    """Test that backup_limit=0 disables backup creation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_limit=0)

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Save again - should NOT create backup
    storage.save([Todo(id=1, text="updated")])

    # No backups should exist
    backups = storage.list_backups()
    assert len(backups) == 0


def test_backup_disabled_via_enable_backups_false(tmp_path) -> None:
    """Test that enable_backups=False disables backup creation."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), enable_backups=False)

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Save again - should NOT create backup
    storage.save([Todo(id=1, text="updated")])

    # No backups should exist
    backups = storage.list_backups()
    assert len(backups) == 0


def test_list_backups_returns_correct_backup_files(tmp_path) -> None:
    """Test that list_backups returns only valid backup files."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos and save
    storage.save([Todo(id=1, text="initial")])

    # Create some extra files that should NOT be in backups list
    (tmp_path / ".todo.json.bak").write_text("not a backup")  # No timestamp
    (tmp_path / ".todo.json.tmp").write_text("temp file")
    (tmp_path / "other.json.bak.20250209143000").write_text("other")

    # Save again to create valid backup
    storage.save([Todo(id=1, text="updated")])

    backups = storage.list_backups()
    assert len(backups) == 1
    assert backups[0].name.startswith(".todo.json.bak.")
    assert re.search(r"\.bak\.\d{14}$", backups[0].name)


def test_restore_from_backup_correctly_restores_data(tmp_path) -> None:
    """Test that restore from backup correctly restores data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save initial todos
    original_todos = [
        Todo(id=1, text="task 1"),
        Todo(id=2, text="task 2", done=True),
        Todo(id=3, text="task 3"),
    ]
    storage.save(original_todos)

    # Modify and save
    storage.save([Todo(id=1, text="corrupted data")])

    # Get backup and restore from it
    backups = storage.list_backups()
    assert len(backups) == 1

    storage.restore(backups[0])

    # Verify data was restored correctly
    restored_todos = storage.load()
    assert len(restored_todos) == 3
    assert restored_todos[0].text == "task 1"
    assert restored_todos[1].text == "task 2"
    assert restored_todos[1].done is True
    assert restored_todos[2].text == "task 3"


def test_restore_creates_new_file_if_missing(tmp_path) -> None:
    """Test that restore works when main file doesn't exist."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos and backup
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="backup test")]
    storage.save(original_todos)
    storage.save([Todo(id=1, text="modified")])

    # Delete main file
    db.unlink()

    # Restore should recreate the file
    backups = storage.list_backups()
    storage.restore(backups[0])

    # Verify file was recreated with correct data
    assert db.exists()
    restored_todos = storage.load()
    assert len(restored_todos) == 2
    assert restored_todos[0].text == "original"
    assert restored_todos[1].text == "backup test"


def test_default_backup_limit_is_three(tmp_path) -> None:
    """Test that default backup limit is 3."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))  # Using default backup_limit

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Create 5 backups
    for i in range(5):
        storage.save([Todo(id=1, text=f"version {i}")])
        time.sleep(0.01)  # Ensure different timestamps

    # Should keep only 3 (default limit)
    backups = storage.list_backups()
    assert len(backups) == 3


def test_backup_uses_same_directory_as_target(tmp_path) -> None:
    """Test that backups are created in same directory as target file."""
    db = tmp_path / "subdir" / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial todos and save
    storage.save([Todo(id=1, text="initial")])
    storage.save([Todo(id=1, text="updated")])

    # Backup should be in same directory as target
    backups = storage.list_backups()
    assert len(backups) == 1
    assert backups[0].parent == db.parent


def test_multiple_saves_create_multiple_backups(tmp_path) -> None:
    """Test that multiple saves create multiple timestamped backups."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_limit=10)

    # Create initial
    storage.save([Todo(id=1, text="v0")])

    # Create multiple saves
    for i in range(5):
        storage.save([Todo(id=1, text=f"v{i}")])
        time.sleep(0.01)  # Ensure different timestamps

    # Should have 5 backups
    backups = storage.list_backups()
    assert len(backups) == 5

    # All should have unique timestamps
    timestamps = [b.name for b in backups]
    assert len(timestamps) == len(set(timestamps))


def test_backup_timestamp_format(tmp_path) -> None:
    """Test that backup timestamps use correct format (YYYYMMDDHHMMSS)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="initial")])
    storage.save([Todo(id=1, text="updated")])

    backups = storage.list_backups()
    assert len(backups) == 1

    # Verify format: .todo.json.bak.YYYYMMDDHHMMSS
    pattern = re.compile(r"\.todo\.json\.bak\.\d{14}$")
    assert pattern.match(backups[0].name)


def test_restore_preserves_backup_file(tmp_path) -> None:
    """Test that restore doesn't delete the backup file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create backup
    storage.save([Todo(id=1, text="original")])
    storage.save([Todo(id=1, text="modified")])

    backups_before = storage.list_backups()
    assert len(backups_before) == 1

    # Restore
    storage.restore(backups_before[0])

    # Backup should still exist
    backups_after = storage.list_backups()
    assert len(backups_after) == 1
    assert backups_after[0] == backups_before[0]
