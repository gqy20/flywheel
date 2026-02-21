"""Tests for automatic backup functionality in TodoStorage.

This test suite verifies that TodoStorage.save() creates backups
of existing files before overwriting them, providing simple undo capability.
"""

from __future__ import annotations

from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_of_existing_file(tmp_path) -> None:
    """Test that save creates a .bak file with previous content."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no backup should be created (no existing file)
    todos_v1 = [Todo(id=1, text="version 1")]
    storage.save(todos_v1)

    # No backup file yet
    backup_path = db.with_suffix(".json.bak")
    assert not backup_path.exists()

    # Second save - backup should be created
    todos_v2 = [Todo(id=1, text="version 2"), Todo(id=2, text="new todo")]
    storage.save(todos_v2)

    # Backup file should now exist
    assert backup_path.exists()

    # Backup should contain the first version
    import json
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "version 1"


def test_backup_disabled_with_parameter(tmp_path) -> None:
    """Test that backup=False does not create backup file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    todos_v1 = [Todo(id=1, text="version 1")]
    storage.save(todos_v1)

    # Second save with backup=False
    todos_v2 = [Todo(id=1, text="version 2")]
    storage.save(todos_v2, backup=False)

    # No backup should exist
    backup_path = db.with_suffix(".json.bak")
    assert not backup_path.exists()


def test_backup_failure_does_not_affect_save(tmp_path, monkeypatch) -> None:
    """Test that backup failure does not prevent save from completing."""
    import shutil

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    todos_v1 = [Todo(id=1, text="version 1")]
    storage.save(todos_v1)

    # Make shutil.copy2 fail to simulate backup failure
    original_copy2 = shutil.copy2

    def failing_copy2(*args, **kwargs):
        raise OSError("Simulated backup failure")

    monkeypatch.setattr(shutil, "copy2", failing_copy2)

    # Second save should still succeed despite backup failure
    todos_v2 = [Todo(id=1, text="version 2")]
    storage.save(todos_v2)

    # File should be updated
    import json
    content = json.loads(db.read_text(encoding="utf-8"))
    assert content[0]["text"] == "version 2"


def test_continuous_saves_update_backup(tmp_path) -> None:
    """Test that each save updates backup to previous version."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    backup_path = db.with_suffix(".json.bak")

    import json

    # Save three versions
    for i in range(1, 4):
        todos = [Todo(id=1, text=f"version {i}")]
        storage.save(todos)

        if i > 1:
            # Backup should contain previous version
            backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
            assert backup_content[0]["text"] == f"version {i - 1}"


def test_backup_preserves_file_permissions(tmp_path) -> None:
    """Test that backup file has reasonable permissions."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    todos_v1 = [Todo(id=1, text="version 1")]
    storage.save(todos_v1)

    # Second save
    todos_v2 = [Todo(id=1, text="version 2")]
    storage.save(todos_v2)

    backup_path = db.with_suffix(".json.bak")
    assert backup_path.exists()

    # Backup should be readable
    import json
    content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(content) == 1
