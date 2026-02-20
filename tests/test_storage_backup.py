"""Tests for automatic backup mechanism in TodoStorage.

This test suite verifies that TodoStorage.save() can create backup files
before overwriting existing data, providing a recovery mechanism.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_when_enabled(tmp_path: Path) -> None:
    """Test that save creates a .bak file when backup=True."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Save again with backup enabled
    new_todos = [Todo(id=1, text="updated task"), Todo(id=2, text="new task")]
    storage.save(new_todos, backup=True)

    # Backup file should exist (todo.json.bak)
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup file should be created"

    # Backup should contain original content
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "original task"


def test_backup_disabled_by_default(tmp_path: Path) -> None:
    """Test that backup is disabled by default (backup=False)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Save again without backup
    new_todos = [Todo(id=1, text="updated task")]
    storage.save(new_todos)

    # No backup file should exist
    backup_path = tmp_path / ".todo.json.bak"
    assert not backup_path.exists(), "Backup file should NOT be created when backup=False"


def test_backup_file_has_same_permissions_as_original(tmp_path: Path) -> None:
    """Test that backup file has restrictive permissions (0600)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task")]
    storage.save(original_todos)

    # Save with backup
    new_todos = [Todo(id=1, text="updated task")]
    storage.save(new_todos, backup=True)

    # Check backup file permissions
    backup_path = tmp_path / "todo.json.bak"
    backup_stat = backup_path.stat()
    backup_mode = stat.S_IMODE(backup_stat.st_mode)

    # Should be 0600 (rw-------)
    assert backup_mode == stat.S_IRUSR | stat.S_IWUSR, (
        f"Backup file should have 0600 permissions, got {oct(backup_mode)}"
    )


def test_multiple_saves_update_backup(tmp_path: Path) -> None:
    """Test that multiple saves with backup update the backup file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    todos1 = [Todo(id=1, text="first")]
    storage.save(todos1)

    # Second save with backup
    todos2 = [Todo(id=1, text="second")]
    storage.save(todos2, backup=True)
    backup_path = tmp_path / "todo.json.bak"
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "first"

    # Third save with backup
    todos3 = [Todo(id=1, text="third")]
    storage.save(todos3, backup=True)
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "second"


def test_no_backup_on_first_save(tmp_path: Path) -> None:
    """Test that backup is not created when no file exists yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save with backup enabled (no existing file to backup)
    todos = [Todo(id=1, text="first save")]
    storage.save(todos, backup=True)

    # No backup should exist since there was no original file
    backup_path = tmp_path / ".todo.json.bak"
    assert not backup_path.exists(), "No backup should be created for first save"


def test_backup_content_matches_original(tmp_path: Path) -> None:
    """Test that backup content exactly matches the original file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data with special characters
    original_todos = [
        Todo(id=1, text="task with unicode: 你好"),
        Todo(id=2, text='task with "quotes"', done=True),
    ]
    storage.save(original_todos)

    # Get original content
    original_content = db.read_text(encoding="utf-8")

    # Save with backup
    new_todos = [Todo(id=1, text="updated")]
    storage.save(new_todos, backup=True)

    # Backup content should match original exactly
    backup_path = tmp_path / "todo.json.bak"
    backup_content = backup_path.read_text(encoding="utf-8")
    assert backup_content == original_content, "Backup should contain exact original content"


def test_storage_instance_backup_config(tmp_path: Path) -> None:
    """Test that backup can be configured at storage instance level."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=True)

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Save again (backup should be automatic)
    new_todos = [Todo(id=1, text="updated")]
    storage.save(new_todos)

    # Backup file should exist due to instance-level config
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup should be created based on instance config"


def test_explicit_backup_false_overrides_instance_config(tmp_path: Path) -> None:
    """Test that explicit backup=False overrides instance-level config."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=True)

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Save with explicit backup=False
    new_todos = [Todo(id=1, text="updated")]
    storage.save(new_todos, backup=False)

    # No backup should be created
    backup_path = tmp_path / ".todo.json.bak"
    assert not backup_path.exists(), "Explicit backup=False should override instance config"
