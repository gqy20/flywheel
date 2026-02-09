"""Tests for file backup before overwrites (Issue #2468).

These tests verify that:
1. Backup files are created with timestamp suffix before overwriting
2. Backup can be disabled via constructor parameter
3. Backup creation failure does not prevent save from succeeding
"""

from __future__ import annotations

import re
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_file_created_on_save_when_file_exists(tmp_path) -> None:
    """A backup file should be created when saving to an existing file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no backup should be created (file doesn't exist yet)
    todos1 = [Todo(id=1, text="original")]
    storage.save(todos1)

    # No backup files should exist after first save
    backup_files = list(tmp_path.glob(".todo.json.*.bak"))
    assert len(backup_files) == 0, "No backup should be created on first save"

    # Second save - backup should be created
    todos2 = [Todo(id=1, text="updated")]
    storage.save(todos2)

    # Backup file should exist
    backup_files = list(tmp_path.glob(".todo.json.*.bak"))
    assert len(backup_files) == 1, "Backup file should be created on second save"

    # Backup should contain the original content
    backup_content = backup_files[0].read_text(encoding="utf-8")
    assert '"text": "original"' in backup_content


def test_backup_disabled_when_backup_false(tmp_path) -> None:
    """No backup should be created when backup=False in constructor."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), backup=False)

    # First save
    todos1 = [Todo(id=1, text="original")]
    storage.save(todos1)

    # Second save - no backup should be created
    todos2 = [Todo(id=1, text="updated")]
    storage.save(todos2)

    # No backup files should exist
    backup_files = list(tmp_path.glob(".todo.json.*.bak"))
    assert len(backup_files) == 0, "No backup should be created when backup=False"


def test_backup_file_has_correct_timestamp_format(tmp_path) -> None:
    """Backup filename should have format .todo.json.YYYYMMDD_HHMMSS.bak."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    todos1 = [Todo(id=1, text="original")]
    storage.save(todos1)

    # Second save - creates backup
    todos2 = [Todo(id=1, text="updated")]
    storage.save(todos2)

    # Get backup file
    backup_files = list(tmp_path.glob(".todo.json.*.bak"))
    assert len(backup_files) == 1

    # Check filename format matches expected pattern
    # Pattern: .todo.json.YYYYMMDD_HHMMSS_N.bak (where N is optional counter)
    backup_name = backup_files[0].name
    pattern = r"\.todo\.json\.\d{8}_\d{6}(?:_\d+)?\.bak"
    assert re.match(pattern, backup_name), f"Backup filename {backup_name} doesn't match pattern {pattern}"


def test_save_succeeds_even_when_backup_creation_fails(tmp_path) -> None:
    """Save should succeed even when backup creation fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    todos1 = [Todo(id=1, text="original")]
    storage.save(todos1)

    # Mock shutil.copy2 to fail
    def failing_copy2(src, dst):
        raise OSError("Simulated backup failure")

    import shutil
    original = shutil.copy2

    with patch.object(shutil, "copy2", failing_copy2):
        # Save should still succeed despite backup failure
        todos2 = [Todo(id=1, text="updated")]
        storage.save(todos2)

    # Restore original
    shutil.copy2 = original

    # Main file should have been updated
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "updated"


def test_no_backup_on_first_save(tmp_path) -> None:
    """No backup should be created when file doesn't exist yet."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - file doesn't exist
    todos = [Todo(id=1, text="first todo")]
    storage.save(todos)

    # No backup files should exist
    backup_files = list(tmp_path.glob(".todo.json.*.bak"))
    assert len(backup_files) == 0, "No backup should be created on first save"


def test_multiple_saves_create_multiple_backups(tmp_path) -> None:
    """Each save should create a new backup file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no backup
    storage.save([Todo(id=1, text="v1")])

    # Second save - creates first backup
    storage.save([Todo(id=1, text="v2")])

    # Third save - creates second backup
    storage.save([Todo(id=1, text="v3")])

    # Two backup files should exist
    backup_files = list(tmp_path.glob(".todo.json.*.bak"))
    assert len(backup_files) == 2, "Multiple saves should create multiple backups"
