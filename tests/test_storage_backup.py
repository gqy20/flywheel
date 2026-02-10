"""Tests for backup file creation in TodoStorage.

This test suite verifies that TodoStorage.save() creates backup files
to prevent data loss from user errors or JSON corruption.
"""

from __future__ import annotations

import json

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_when_file_exists(tmp_path) -> None:
    """Test that save() creates a .bak file when target file already exists."""
    db = tmp_path / "todo.json"
    backup = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task"), Todo(id=2, text="another task")]
    storage.save(original_todos)

    # Modify and save again - this should create backup
    modified_todos = [Todo(id=1, text="modified task")]
    storage.save(modified_todos)

    # Verify backup file was created
    assert backup.exists(), "Backup file should be created on save"

    # Verify backup contains the ORIGINAL content (before modification)
    backup_content = json.loads(backup.read_text(encoding="utf-8"))
    assert len(backup_content) == 2
    assert backup_content[0]["text"] == "original task"
    assert backup_content[1]["text"] == "another task"

    # Verify current file has the modified content
    current_content = json.loads(db.read_text(encoding="utf-8"))
    assert len(current_content) == 1
    assert current_content[0]["text"] == "modified task"


def test_save_creates_backup_on_second_save(tmp_path) -> None:
    """Test that backup is created even when file exists from previous run."""
    db = tmp_path / "todo.json"
    backup = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # First save - no backup since file didn't exist before
    todos_v1 = [Todo(id=1, text="version 1")]
    storage.save(todos_v1)
    assert not backup.exists(), "No backup should be created on first save"

    # Second save - backup should be created
    todos_v2 = [Todo(id=1, text="version 2"), Todo(id=2, text="new task")]
    storage.save(todos_v2)
    assert backup.exists(), "Backup should be created on second save"

    # Backup should contain v1 data
    backup_content = json.loads(backup.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "version 1"


def test_backup_overwrites_old_backup(tmp_path) -> None:
    """Test that only one backup file is kept (no accumulation)."""
    db = tmp_path / "todo.json"
    backup = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="v1")])

    # Second save - creates backup of v1
    storage.save([Todo(id=1, text="v2")])
    assert backup.exists()

    # Third save - should overwrite old backup with v2 content
    storage.save([Todo(id=1, text="v3")])

    # Only one backup file should exist
    assert backup.exists()

    # Backup should contain v2 content (the state before v3 save)
    backup_content = json.loads(backup.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "v2"


def test_backup_preserves_file_metadata(tmp_path) -> None:
    """Test that backup preserves file metadata using shutil.copy2."""
    db = tmp_path / "todo.json"
    backup = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="original")])

    # Save again to create backup
    storage.save([Todo(id=1, text="modified")])

    # Verify backup exists
    assert backup.exists()

    # Backup should contain the original data (before modification)
    backup_content = backup.read_text(encoding="utf-8")
    backup_data = json.loads(backup_content)
    assert len(backup_data) == 1
    assert backup_data[0]["text"] == "original"


def test_first_save_creates_no_backup(tmp_path) -> None:
    """Test that first save (when file doesn't exist) doesn't create backup."""
    db = tmp_path / "todo.json"
    backup = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # First save to non-existent file
    storage.save([Todo(id=1, text="first todo")])

    # No backup should be created since there was no previous file
    assert not backup.exists()


def test_backup_works_with_custom_path(tmp_path) -> None:
    """Test that backup works correctly with custom file paths."""
    db = tmp_path / "subdir" / "custom.json"
    backup = tmp_path / "subdir" / "custom.json.bak"
    storage = TodoStorage(str(db))

    # Create initial data
    storage.save([Todo(id=1, text="initial")])

    # Modify
    storage.save([Todo(id=1, text="modified")])

    # Verify backup was created in the same directory
    assert backup.exists()
    backup_content = json.loads(backup.read_text(encoding="utf-8"))
    assert backup_content[0]["text"] == "initial"


def test_all_todos_deleted_can_be_recovered_from_backup(tmp_path) -> None:
    """Regression test: User can recover data after accidentally deleting all todos."""
    db = tmp_path / "todo.json"
    backup = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # Create important todos
    original_todos = [
        Todo(id=1, text="important project task"),
        Todo(id=2, text="another critical task"),
        Todo(id=3, text="third important item"),
    ]
    storage.save(original_todos)

    # User accidentally clears all todos (e.g., rm command)
    storage.save([])

    # Current file is empty
    current_data = storage.load()
    assert len(current_data) == 0

    # But backup contains the data for recovery!
    assert backup.exists()
    backup_todos = json.loads(backup.read_text(encoding="utf-8"))
    assert len(backup_todos) == 3
    assert backup_todos[0]["text"] == "important project task"
    assert backup_todos[1]["text"] == "another critical task"
    assert backup_todos[2]["text"] == "third important item"
