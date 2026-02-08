"""Tests for automatic backup before save in TodoStorage.

This test suite verifies that TodoStorage.save() creates backups
of the previous state before each save operation to prevent data loss.
"""

from __future__ import annotations

import json

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_creates_backup_when_file_exists(tmp_path) -> None:
    """Test that save creates a .bak backup when previous file exists."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Verify no backup exists yet (first save, no previous file to backup)
    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists()

    # Save again - should create backup
    new_todos = [Todo(id=1, text="modified")]
    storage.save(new_todos)

    # Verify backup was created with original content
    assert backup_path.exists()
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 1
    assert backup_content[0]["text"] == "original"


def test_save_rotates_backups_with_limit(tmp_path) -> None:
    """Test that backups rotate with configurable limit (default 3)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="v1")])

    # Perform multiple saves to create backups
    storage.save([Todo(id=1, text="v2")])
    storage.save([Todo(id=1, text="v3")])
    storage.save([Todo(id=1, text="v4")])

    # With default limit of 3, we should have:
    # - todo.json.bak (v3)
    # - todo.json.bak.1 (v2)
    # - todo.json.bak.2 (v1)
    backup_path = tmp_path / "todo.json.bak"
    backup_1 = tmp_path / "todo.json.bak.1"
    backup_2 = tmp_path / "todo.json.bak.2"

    assert backup_path.exists()
    assert backup_1.exists()
    assert backup_2.exists()

    # Verify rotation order (bak should be most recent)
    content_bak = json.loads(backup_path.read_text(encoding="utf-8"))
    content_1 = json.loads(backup_1.read_text(encoding="utf-8"))
    content_2 = json.loads(backup_2.read_text(encoding="utf-8"))

    assert content_bak[0]["text"] == "v3"
    assert content_1[0]["text"] == "v2"
    assert content_2[0]["text"] == "v1"


def test_backup_deleted_when_limit_exceeded(tmp_path) -> None:
    """Test that oldest backup is deleted when limit is exceeded."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_limit=2)

    # Create initial file and perform saves
    storage.save([Todo(id=1, text="v1")])
    storage.save([Todo(id=1, text="v2")])
    storage.save([Todo(id=1, text="v3")])

    # With limit of 2, we should only have:
    # - todo.json.bak (v2)
    # - todo.json.bak.1 (v1)
    # No todo.json.bak.2 should exist (would have contained v0)
    backup_path = tmp_path / "todo.json.bak"
    backup_1 = tmp_path / "todo.json.bak.1"
    backup_2 = tmp_path / "todo.json.bak.2"

    assert backup_path.exists()
    assert backup_1.exists()
    assert not backup_2.exists()


def test_load_fallback_to_backup_when_corrupted(tmp_path) -> None:
    """Test that load can fallback to backup when main file is corrupted."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    original_todos = [Todo(id=1, text="backup_data"), Todo(id=2, text="recovery")]
    storage.save(original_todos)

    # Save again to create backup
    storage.save([Todo(id=1, text="current")])

    # Corrupt the main file
    db.write_text("invalid json {{", encoding="utf-8")

    # Load should fallback to backup when use_backup=True
    recovered = storage.load(use_backup=True)

    assert len(recovered) == 2
    assert recovered[0].text == "backup_data"
    assert recovered[1].text == "recovery"


def test_no_backup_on_first_save(tmp_path) -> None:
    """Test that no backup is created on first save (no previous file)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="first")])

    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists()


def test_backup_with_custom_limit(tmp_path) -> None:
    """Test that backup limit can be customized."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup_limit=5)

    # Create initial file
    storage.save([Todo(id=1, text="v1")])

    # Perform multiple saves
    for i in range(2, 8):
        storage.save([Todo(id=1, text=f"v{i}")])

    # Should have 5 backups total
    backup_path = tmp_path / "todo.json.bak"
    backup_1 = tmp_path / "todo.json.bak.1"
    backup_2 = tmp_path / "todo.json.bak.2"
    backup_3 = tmp_path / "todo.json.bak.3"
    backup_4 = tmp_path / "todo.json.bak.4"

    assert backup_path.exists()
    assert backup_1.exists()
    assert backup_2.exists()
    assert backup_3.exists()
    assert backup_4.exists()

    # todo.json.bak.5 should not exist (would have been v1, deleted due to limit)
    backup_5 = tmp_path / "todo.json.bak.5"
    assert not backup_5.exists()
