"""Tests for backup functionality in TodoStorage.

This test suite verifies that TodoStorage.save() creates a backup
of the existing file before overwriting it.
"""

from __future__ import annotations

import json
from pathlib import Path

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_first_save_does_not_create_backup(tmp_path: Path) -> None:
    """Test that first save (no existing file) does not create a backup file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save for the first time - file doesn't exist yet
    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # Verify the main file was created
    assert db.exists()

    # Verify no backup file was created (since there was nothing to backup)
    backup_path = Path(str(db) + ".bak")
    assert not backup_path.exists()


def test_save_creates_backup_when_overwriting_existing_file(tmp_path: Path) -> None:
    """Test that save creates a .bak backup of existing file before overwriting."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Get original content for comparison
    original_content = db.read_text(encoding="utf-8")

    # Now save new data - should backup the existing file
    new_todos = [Todo(id=1, text="new")]
    storage.save(new_todos)

    # Verify backup file was created
    backup_path = Path(str(db) + ".bak")
    assert backup_path.exists(), "Backup file should be created when overwriting"

    # Verify backup content matches original content
    backup_content = backup_path.read_text(encoding="utf-8")
    assert backup_content == original_content, "Backup should contain original data"

    # Verify main file now has new content
    new_content = db.read_text(encoding="utf-8")
    parsed_new = json.loads(new_content)
    assert len(parsed_new) == 1
    assert parsed_new[0]["text"] == "new"


def test_backup_content_matches_original_before_overwrite(tmp_path: Path) -> None:
    """Test that .bak file content exactly matches what was there before the overwrite."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file with specific content
    initial_todos = [
        Todo(id=1, text="first todo"),
        Todo(id=2, text="second todo", done=True),
        Todo(id=3, text="third"),
    ]
    storage.save(initial_todos)
    initial_content = db.read_text(encoding="utf-8")

    # Save new data
    storage.save([Todo(id=10, text="replaced")])

    # Verify backup matches initial content exactly
    backup_path = Path(str(db) + ".bak")
    backup_content = backup_path.read_text(encoding="utf-8")
    assert backup_content == initial_content

    # Parse backup to verify it contains the initial todos
    backup_data = json.loads(backup_content)
    assert len(backup_data) == 3
    assert backup_data[0]["text"] == "first todo"
    assert backup_data[1]["done"] is True


def test_backup_replaced_on_subsequent_save(tmp_path: Path) -> None:
    """Test that each save replaces the backup, not appending multiple backups."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="v1")])
    v1_content = db.read_text(encoding="utf-8")

    # Second save - backup should contain v1
    storage.save([Todo(id=1, text="v2")])
    backup_path = Path(str(db) + ".bak")
    assert backup_path.read_text(encoding="utf-8") == v1_content
    v2_content = db.read_text(encoding="utf-8")

    # Third save - backup should now contain v2, not v1
    storage.save([Todo(id=1, text="v3")])
    assert backup_path.read_text(encoding="utf-8") == v2_content
    assert db.read_text(encoding="utf-8") != v1_content  # Current is v3, not v1


def test_backup_failure_does_not_block_save(tmp_path: Path) -> None:
    """Test that backup failure logs a warning but does not block the main save operation.

    This tests the acceptance criteria: '备份失败不阻塞主保存操作（记录警告即可）'
    """
    from unittest.mock import patch

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    storage.save([Todo(id=1, text="original")])
    assert db.exists()

    # Simulate backup failure by making shutil.copy2 raise an error
    # But the save should still succeed
    with patch("shutil.copy2", side_effect=OSError("Backup failed")):
        # This should NOT raise - backup failure is non-blocking
        storage.save([Todo(id=1, text="new")])

    # Verify the main save succeeded despite backup failure
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "new"
