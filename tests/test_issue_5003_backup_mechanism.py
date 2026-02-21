"""Tests for file backup mechanism in TodoStorage.

This test suite verifies that TodoStorage.save() creates backup files
before overwriting existing data, preventing accidental data loss.

Issue: #5003
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_of_existing_file(tmp_path: Path) -> None:
    """Test that save creates a .bak file with previous content."""
    db = tmp_path / "todo.json"
    backup_file = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # First save - creates initial data
    first_todos = [Todo(id=1, text="first todo")]
    storage.save(first_todos)

    # Backup should not exist after first save (no previous file to backup)
    assert not backup_file.exists()

    # Second save - should create backup of first data
    second_todos = [Todo(id=1, text="second todo"), Todo(id=2, text="new todo")]
    storage.save(second_todos)

    # Backup should now exist
    assert backup_file.exists(), "Backup file should be created after second save"

    # Backup should contain first data
    backup_content = json.loads(backup_file.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "first todo"


def test_first_save_does_not_create_backup(tmp_path: Path) -> None:
    """Test that first save (no existing file) does not create backup."""
    db = tmp_path / "todo.json"
    backup_file = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # No backup should exist
    assert not backup_file.exists()


def test_consecutive_saves_update_backup(tmp_path: Path) -> None:
    """Test that consecutive saves update the backup to previous version."""
    db = tmp_path / "todo.json"
    backup_file = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="version 1")])

    # Second save - backup becomes version 1
    storage.save([Todo(id=1, text="version 2")])
    backup_content = json.loads(backup_file.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "version 1"

    # Third save - backup becomes version 2
    storage.save([Todo(id=1, text="version 3")])
    backup_content = json.loads(backup_file.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "version 2"


def test_backup_is_disabled_by_flag(tmp_path: Path) -> None:
    """Test that backup can be disabled via constructor parameter."""
    db = tmp_path / "todo.json"
    backup_file = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db), backup=False)

    # First save
    storage.save([Todo(id=1, text="first")])

    # Second save - should NOT create backup since backup=False
    storage.save([Todo(id=1, text="second")])

    # No backup should exist
    assert not backup_file.exists()


def test_backup_preserves_complete_file_content(tmp_path: Path) -> None:
    """Test that backup preserves complete data including unicode and special chars."""
    db = tmp_path / "todo.json"
    backup_file = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # Create todos with special content
    original_todos = [
        Todo(id=1, text="task with unicode: 你好世界 🌍"),
        Todo(id=2, text='task with "quotes" and \\n', done=True),
        Todo(id=3, text="normal task"),
    ]
    storage.save(original_todos)

    # Overwrite with new data
    storage.save([Todo(id=1, text="new data")])

    # Backup should have exact original content
    backup_content = json.loads(backup_file.read_text(encoding="utf-8"))
    assert len(backup_content) == 3
    assert backup_content[0]["text"] == "task with unicode: 你好世界 🌍"
    assert backup_content[1]["text"] == 'task with "quotes" and \\n'
    assert backup_content[1]["done"] is True
    assert backup_content[2]["text"] == "normal task"
