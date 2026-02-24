"""Tests for file backup feature in TodoStorage.

This test suite verifies that TodoStorage.save() creates a backup
of the existing file before overwriting it.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_of_existing_file(tmp_path) -> None:
    """Test that save() creates .bak file with old content when overwriting."""
    db = tmp_path / "todo.json"
    backup = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # First save - creates initial file
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Verify no backup yet (first save, no previous file)
    assert not backup.exists()

    # Second save - should create backup
    new_todos = [Todo(id=1, text="new content")]
    storage.save(new_todos)

    # Backup should exist with original content
    assert backup.exists()
    backup_data = json.loads(backup.read_text(encoding="utf-8"))
    assert len(backup_data) == 2
    assert backup_data[0]["text"] == "original"
    assert backup_data[1]["text"] == "data"

    # Main file should have new content
    main_data = json.loads(db.read_text(encoding="utf-8"))
    assert len(main_data) == 1
    assert main_data[0]["text"] == "new content"


def test_first_save_does_not_create_backup(tmp_path) -> None:
    """Test that first save (no existing file) does not create backup."""
    db = tmp_path / "todo.json"
    backup = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # First save - no previous file exists
    todos = [Todo(id=1, text="first save")]
    storage.save(todos)

    # No backup should be created since there was no original file
    assert not backup.exists()

    # Main file should have the data
    main_data = json.loads(db.read_text(encoding="utf-8"))
    assert len(main_data) == 1
    assert main_data[0]["text"] == "first save"


def test_backup_disabled_with_backup_false(tmp_path) -> None:
    """Test that backup=False disables backup creation."""
    db = tmp_path / "todo.json"
    backup = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db), backup=False)

    # First save
    storage.save([Todo(id=1, text="original")])

    # Second save - should NOT create backup because backup=False
    storage.save([Todo(id=1, text="new")])

    # No backup should exist
    assert not backup.exists()

    # Main file should have new content
    main_data = json.loads(db.read_text(encoding="utf-8"))
    assert main_data[0]["text"] == "new"


def test_backup_failure_does_not_block_save(tmp_path, caplog) -> None:
    """Test that backup failure logs warning but does not prevent save."""
    import shutil

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=True)

    # First save
    storage.save([Todo(id=1, text="original")])

    # Make shutil.copy2 fail to simulate backup failure
    original_copy2 = shutil.copy2

    def failing_copy2(src, dst):
        if str(dst).endswith(".bak"):
            raise OSError("Simulated backup failure")
        return original_copy2(src, dst)

    with patch.object(shutil, "copy2", failing_copy2):
        # This should NOT raise - backup failure should be logged, not block
        storage.save([Todo(id=1, text="new")])

    # Main file should still be saved successfully
    main_data = json.loads(db.read_text(encoding="utf-8"))
    assert main_data[0]["text"] == "new"

    # Warning should be logged
    assert any("backup" in record.message.lower() for record in caplog.records)


def test_backup_preserves_most_recent_backup_only(tmp_path) -> None:
    """Test that backup always contains the most recently overwritten content."""
    db = tmp_path / "todo.json"
    backup = tmp_path / "todo.json.bak"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="version 1")])
    assert not backup.exists()

    # Second save - backup should be "version 1"
    storage.save([Todo(id=1, text="version 2")])
    backup_data = json.loads(backup.read_text(encoding="utf-8"))
    assert backup_data[0]["text"] == "version 1"

    # Third save - backup should now be "version 2"
    storage.save([Todo(id=1, text="version 3")])
    backup_data = json.loads(backup.read_text(encoding="utf-8"))
    assert backup_data[0]["text"] == "version 2"

    # Main file should be "version 3"
    main_data = json.loads(db.read_text(encoding="utf-8"))
    assert main_data[0]["text"] == "version 3"
