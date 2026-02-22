"""Tests for file backup mechanism in TodoStorage.

This test suite verifies that TodoStorage can optionally create backup files
before overwriting the main database file.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_false_does_not_create_bak_file(tmp_path) -> None:
    """Verify backup=False (default) does not create .bak file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))  # default backup=False

    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # No backup file should exist
    bak_path = tmp_path / "todo.json.bak"
    assert not bak_path.exists()


def test_backup_false_explicit_does_not_create_bak_file(tmp_path) -> None:
    """Verify backup=False explicitly does not create .bak file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=False)

    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # No backup file should exist
    bak_path = tmp_path / "todo.json.bak"
    assert not bak_path.exists()


def test_backup_true_creates_bak_with_previous_data(tmp_path) -> None:
    """Verify backup=True creates .bak with previous data before save."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=True)

    # First save - no backup since no existing file
    first_todos = [Todo(id=1, text="first")]
    storage.save(first_todos)

    bak_path = tmp_path / "todo.json.bak"
    # No backup yet because there was nothing to backup
    assert not bak_path.exists()

    # Second save - should backup first data
    second_todos = [Todo(id=1, text="second"), Todo(id=2, text="added")]
    storage.save(second_todos)

    # Backup should now exist
    assert bak_path.exists()

    # Backup should contain first data
    bak_content = json.loads(bak_path.read_text(encoding="utf-8"))
    assert len(bak_content) == 1
    assert bak_content[0]["text"] == "first"

    # Main file should contain second data
    main_content = json.loads(db.read_text(encoding="utf-8"))
    assert len(main_content) == 2
    assert main_content[0]["text"] == "second"


def test_backup_true_no_backup_on_first_save(tmp_path) -> None:
    """Verify no backup is created when file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=True)

    todos = [Todo(id=1, text="initial")]
    storage.save(todos)

    # No backup since there was no existing file
    bak_path = tmp_path / "todo.json.bak"
    assert not bak_path.exists()

    # Main file should exist
    assert db.exists()


def test_backup_multiple_saves_keeps_last_backup(tmp_path) -> None:
    """Verify consecutive saves update .bak with previous content."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=True)

    # First save
    storage.save([Todo(id=1, text="v1")])
    # Second save - backup v1
    storage.save([Todo(id=1, text="v2")])
    # Third save - backup v2
    storage.save([Todo(id=1, text="v3")])

    bak_path = tmp_path / "todo.json.bak"
    bak_content = json.loads(bak_path.read_text(encoding="utf-8"))
    # Backup should contain v2 (the previous version before v3)
    assert bak_content[0]["text"] == "v2"

    # Main should contain v3
    main_content = json.loads(db.read_text(encoding="utf-8"))
    assert main_content[0]["text"] == "v3"


def test_backup_failure_does_not_block_save(tmp_path, caplog) -> None:
    """Verify backup failure logs warning but doesn't block save."""
    import logging
    caplog.set_level(logging.WARNING)

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=True)

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Mock shutil.copy2 to fail
    with patch("flywheel.storage.shutil.copy2", side_effect=OSError("Backup failed")):
        # Save should still succeed
        storage.save([Todo(id=1, text="updated")])

    # Main file should be updated
    main_content = json.loads(db.read_text(encoding="utf-8"))
    assert main_content[0]["text"] == "updated"

    # Warning should be logged
    assert any("Backup failed" in record.message for record in caplog.records)


def test_backup_file_permissions_match_original(tmp_path) -> None:
    """Verify .bak file has same permissions as original file."""
    import stat

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=True)

    # Create initial file
    storage.save([Todo(id=1, text="initial")])

    # Get original permissions
    original_mode = db.stat().st_mode

    # Save again to create backup
    storage.save([Todo(id=1, text="updated")])

    bak_path = tmp_path / "todo.json.bak"
    backup_mode = bak_path.stat().st_mode

    # Permissions should match (at least the permission bits)
    assert stat.S_IMODE(backup_mode) == stat.S_IMODE(original_mode)
