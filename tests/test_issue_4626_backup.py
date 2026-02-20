"""Tests for backup functionality in TodoStorage.

This test suite verifies that TodoStorage.save() creates a backup
of the existing file before overwriting it, as per issue #4626.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_first_save_creates_no_backup(tmp_path) -> None:
    """Test that first save does not create a backup file.

    Backup should only be created when overwriting an existing file.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save - no existing file, so no backup should be created
    todos = [Todo(id=1, text="first save")]
    storage.save(todos)

    # Verify main file exists
    assert db.exists()

    # Verify no backup file was created
    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists()


def test_overwrite_creates_backup(tmp_path) -> None:
    """Test that overwriting an existing file creates a .bak backup.

    This is the main feature: when save() is called on an existing file,
    the old file should be backed up with .bak extension before overwrite.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    original_todos = [Todo(id=1, text="original"), Todo(id=2, text="data")]
    storage.save(original_todos)

    # Get original content for comparison
    original_content = db.read_text(encoding="utf-8")

    # Save new data (this should create backup)
    new_todos = [Todo(id=1, text="updated"), Todo(id=2, text="content"), Todo(id=3, text="new")]
    storage.save(new_todos)

    # Verify backup file was created
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists()

    # Verify backup content matches original
    backup_content = backup_path.read_text(encoding="utf-8")
    assert backup_content == original_content


def test_backup_content_matches_overwritten_data(tmp_path) -> None:
    """Test that .bak content matches the file content before overwrite.

    Verifies that the backup contains exactly what was in the file
    before the save operation.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file with specific data
    first_todos = [Todo(id=1, text="first version")]
    storage.save(first_todos)
    first_content = db.read_text(encoding="utf-8")

    # Overwrite with second version
    second_todos = [Todo(id=1, text="second version")]
    storage.save(second_todos)
    second_content = db.read_text(encoding="utf-8")

    # Backup should have first version
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.read_text(encoding="utf-8") == first_content

    # Main file should have second version
    assert db.read_text(encoding="utf-8") == second_content

    # Overwrite again with third version
    third_todos = [Todo(id=1, text="third version")]
    storage.save(third_todos)
    third_content = db.read_text(encoding="utf-8")

    # Backup should now have second version
    assert backup_path.read_text(encoding="utf-8") == second_content

    # Main file should have third version
    assert db.read_text(encoding="utf-8") == third_content


def test_backup_failure_does_not_block_save(tmp_path) -> None:
    """Test that backup failure does not block the main save operation.

    As per the acceptance criteria, backup failure should only log a warning
    but not prevent the actual save from completing.
    """
    from unittest.mock import patch

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Make the backup operation fail by patching shutil.copy2
    with patch("shutil.copy2") as mock_copy:
        mock_copy.side_effect = OSError("Backup failed")

        # This should still succeed even though backup failed
        new_todos = [Todo(id=1, text="new")]
        storage.save(new_todos)

    # Verify main file was still updated
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "new"
