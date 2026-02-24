"""Tests for backup/restore functionality in TodoStorage.

This test suite verifies that TodoStorage provides backup and restore
capabilities to prevent data loss from accidental operations.
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_file(tmp_path) -> None:
    """Test that save() creates a .bak backup file before overwriting."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Save new data
    new_todos = [Todo(id=1, text="new task"), Todo(id=2, text="another task")]
    storage.save(new_todos)

    # Check backup file exists
    backup_path = tmp_path / ".todo.json.bak"
    assert backup_path.exists(), "Backup file should be created"

    # Verify backup contains original data
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "original task"


def test_save_only_keeps_one_backup(tmp_path) -> None:
    """Test that only the most recent backup is kept (not a history)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first")])

    # Second save
    storage.save([Todo(id=1, text="second")])

    # Third save
    storage.save([Todo(id=1, text="third")])

    backup_path = tmp_path / ".todo.json.bak"

    # Backup should contain "second" (previous to current "third")
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "second"


def test_restore_backup_recovers_data(tmp_path) -> None:
    """Test that restore_backup() recovers data from backup file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create and save initial data
    original_todos = [Todo(id=1, text="important data")]
    storage.save(original_todos)

    # Save new data (creates backup)
    storage.save([Todo(id=1, text="accidental overwrite")])

    # Restore from backup
    storage.restore_backup()

    # Verify original data is restored
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "important data"


def test_restore_backup_raises_when_no_backup(tmp_path) -> None:
    """Test that restore_backup() raises error when no backup exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save once (no backup yet since there was no previous file)
    storage.save([Todo(id=1, text="only save")])

    # Remove backup file if it exists
    backup_path = tmp_path / ".todo.json.bak"
    if backup_path.exists():
        backup_path.unlink()

    # Attempting to restore should raise FileNotFoundError
    with pytest.raises(FileNotFoundError, match="No backup file found"):
        storage.restore_backup()


def test_restore_backup_works_when_only_backup_exists(tmp_path) -> None:
    """Test that restore_backup() can restore even when main file was deleted."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data and save twice to create backup
    storage.save([Todo(id=1, text="first")])
    storage.save([Todo(id=1, text="second")])

    # Delete main file (simulating accidental deletion)
    db.unlink()

    # Restore should still work since backup exists
    storage.restore_backup()

    # Verify data is restored from backup
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "first"


def test_save_without_existing_file_creates_no_backup(tmp_path) -> None:
    """Test that first save (no existing file) doesn't create a backup."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no previous file to backup
    storage.save([Todo(id=1, text="first save")])

    backup_path = tmp_path / ".todo.json.bak"
    # Backup should not exist since there was no previous file
    assert not backup_path.exists()


def test_backup_file_has_same_permissions_as_main_file(tmp_path) -> None:
    """Test that backup file permissions match main file permissions."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first")])

    # Second save creates backup
    storage.save([Todo(id=1, text="second")])

    backup_path = tmp_path / ".todo.json.bak"

    # Both files should have the same permissions
    main_stat = db.stat()
    backup_stat = backup_path.stat()

    # Compare permission bits (last 9 bits: rwx for user/group/other)
    main_perms = main_stat.st_mode & 0o777
    backup_perms = backup_stat.st_mode & 0o777

    assert main_perms == backup_perms, (
        f"Permission mismatch: main={oct(main_perms)}, backup={oct(backup_perms)}"
    )


def test_backup_path_property(tmp_path) -> None:
    """Test that backup_path property returns correct path."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    expected_backup = tmp_path / ".todo.json.bak"
    assert storage.backup_path == expected_backup


def test_multiple_saves_maintain_backup_integrity(tmp_path) -> None:
    """Test that multiple saves maintain correct backup integrity."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a sequence of saves
    for i in range(5):
        storage.save([Todo(id=j, text=f"save-{i}-task-{j}") for j in range(3)])

    backup_path = tmp_path / ".todo.json.bak"

    # Backup should contain data from save #3 (second to last, before save #4)
    # Index: 0, 1, 2, 3, 4 - save #4 is the last, backup should have save #3
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 3
    # All tasks should be from save-3
    for item in backup_content:
        assert "save-3" in item["text"]
