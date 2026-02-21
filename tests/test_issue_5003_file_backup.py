"""Tests for file backup mechanism in TodoStorage.

Issue #5003: Add file backup mechanism to prevent accidental data loss.

This test suite verifies that TodoStorage.save() creates a backup of the
existing file before overwriting it, allowing users to recover data if
they accidentally delete important data and save.
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_file(tmp_path: Path) -> None:
    """Test that save() creates a .bak backup file before overwriting."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - creates initial file
    first_todos = [Todo(id=1, text="first save")]
    storage.save(first_todos)

    # Second save - should create backup of first save
    second_todos = [Todo(id=2, text="second save")]
    storage.save(second_todos)

    # Verify backup file exists
    backup_path = tmp_path / ".todo.json.bak"
    assert backup_path.exists(), "Backup file should be created on subsequent saves"

    # Verify backup contains the first save data
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "first save"


def test_first_save_does_not_create_backup(tmp_path: Path) -> None:
    """Test that the first save does not create a backup (no existing file)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no existing file, so no backup needed
    todos = [Todo(id=1, text="first save")]
    storage.save(todos)

    # Verify no backup file exists
    backup_path = tmp_path / ".todo.json.bak"
    assert not backup_path.exists(), "Backup file should not be created on first save"


def test_consecutive_saves_update_backup(tmp_path: Path) -> None:
    """Test that consecutive saves update the backup to the previous version."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="version 1")])

    # Second save - backup should contain version 1
    storage.save([Todo(id=2, text="version 2")])
    backup_path = tmp_path / ".todo.json.bak"
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "version 1"

    # Third save - backup should now contain version 2
    storage.save([Todo(id=3, text="version 3")])
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "version 2"


def test_backup_can_be_used_to_recover_data(tmp_path: Path) -> None:
    """Test that backup file can be used to recover previous data."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data with important items
    important_todos = [
        Todo(id=1, text="important task 1"),
        Todo(id=2, text="important task 2"),
        Todo(id=3, text="important task 3"),
    ]
    storage.save(important_todos)

    # "Accidentally" delete all items and save
    storage.save([])

    # Current file should be empty
    current = storage.load()
    assert len(current) == 0

    # But backup should contain the important data
    backup_path = tmp_path / ".todo.json.bak"
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 3
    assert backup_content[0]["text"] == "important task 1"
    assert backup_content[1]["text"] == "important task 2"
    assert backup_content[2]["text"] == "important task 3"


def test_backup_preserves_unicode_content(tmp_path: Path) -> None:
    """Test that backup correctly preserves unicode content."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save with unicode content
    storage.save([Todo(id=1, text="任务一: 你好世界 🎉")])

    # Second save
    storage.save([Todo(id=2, text="任务二")])

    # Verify backup has unicode preserved
    backup_path = tmp_path / ".todo.json.bak"
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "任务一: 你好世界 🎉"
