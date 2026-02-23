"""Tests for automatic backup functionality in TodoStorage.

This test suite verifies that TodoStorage.save() creates a backup file
before overwriting the existing file, providing a recovery path when
users accidentally overwrite their todos.
"""

from __future__ import annotations

import json
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_file_when_file_exists(tmp_path) -> None:
    """Test that save creates a .bak file containing previous content."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - creates new file, no backup expected
    first_todos = [Todo(id=1, text="first save")]
    storage.save(first_todos)
    first_content = db.read_text(encoding="utf-8")

    # Second save - should create backup with first save's content
    second_todos = [Todo(id=1, text="second save"), Todo(id=2, text="added")]
    storage.save(second_todos)

    # Verify backup file exists (backup is at {path}.bak)
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup file should be created on second save"

    # Verify backup contains first save's content
    backup_content = backup_path.read_text(encoding="utf-8")
    assert backup_content == first_content

    # Verify backup content parses to first save's todos
    backup_data = json.loads(backup_content)
    assert len(backup_data) == 1
    assert backup_data[0]["text"] == "first save"


def test_save_on_new_file_does_not_create_backup(tmp_path) -> None:
    """Test that saving a new file (no existing file) does not create a backup."""
    db = tmp_path / "new_todo.json"
    storage = TodoStorage(str(db))

    # Save to new file
    todos = [Todo(id=1, text="new file")]
    storage.save(todos)

    # No backup should exist (backup is at {path}.bak)
    backup_path = tmp_path / "new_todo.json.bak"
    assert not backup_path.exists(), "Backup should not exist for new file"


def test_backup_has_same_permissions_as_original(tmp_path) -> None:
    """Test that backup file retains the permissions of the original file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first")])

    # Change permissions on the file (more permissive than default)
    db.chmod(0o644)
    original_mode = db.stat().st_mode

    # Second save - should create backup with same permissions
    storage.save([Todo(id=1, text="second")])

    backup_path = tmp_path / "todo.json.bak"
    backup_mode = backup_path.stat().st_mode

    # Permissions should match (at least the permission bits)
    assert stat.S_IMODE(backup_mode) == stat.S_IMODE(original_mode)


def test_backup_rotation_keeps_only_one_backup(tmp_path) -> None:
    """Test that only one backup is kept (no rotation history)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Multiple saves
    for i in range(5):
        storage.save([Todo(id=j, text=f"save-{i}-todo-{j}") for j in range(3)])

    # Only one backup file should exist
    backup_files = list(tmp_path.glob("todo.json.bak*"))
    assert len(backup_files) == 1, f"Expected 1 backup file, got {len(backup_files)}: {backup_files}"

    # The backup should contain the 4th save's content (from save before last)
    backup_path = backup_files[0]
    backup_data = json.loads(backup_path.read_text(encoding="utf-8"))
    # Last backup is from the 4th save (index 3)
    assert backup_data[0]["text"] == "save-3-todo-0"


def test_multiple_saves_maintain_correct_backup(tmp_path) -> None:
    """Test that each save updates the backup to contain previous version."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="version-1")])

    # Second save
    storage.save([Todo(id=1, text="version-2")])
    backup_path = tmp_path / "todo.json.bak"
    assert json.loads(backup_path.read_text())[0]["text"] == "version-1"

    # Third save
    storage.save([Todo(id=1, text="version-3")])
    assert json.loads(backup_path.read_text())[0]["text"] == "version-2"

    # Fourth save
    storage.save([Todo(id=1, text="version-4")])
    assert json.loads(backup_path.read_text())[0]["text"] == "version-3"
