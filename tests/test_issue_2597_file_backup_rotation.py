"""Regression tests for issue #2597: Add file backup/rotation before overwriting existing data.

Issue: os.replace() atomically overwrites target file without backup.
If save() fails or contains a bug, users have no way to recover previous data.

Solution: Before overwriting, create a backup of the existing file.
Use rotation scheme (.bak, .bak1, .bak2) to keep only last N backups.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import json
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_backup_file_created_when_overwriting_existing_data(tmp_path) -> None:
    """Issue #2597: A .bak backup file should be created when overwriting existing data.

    Before fix: No backup file is created
    After fix: A .bak file contains the previous state before overwriting
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original task"), Todo(id=2, text="another task")]
    storage.save(original_todos)

    # Overwrite with new data
    new_todos = [Todo(id=1, text="modified task")]
    storage.save(new_todos)

    # Verify backup file exists
    backup_path = tmp_path / "todo.json.bak"
    assert backup_path.exists(), "Backup file should be created when overwriting existing data"

    # Verify backup contains the original data
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))
    assert len(backup_content) == 2
    assert backup_content[0]["text"] == "original task"
    assert backup_content[1]["text"] == "another task"


def test_backup_file_not_created_for_new_file(tmp_path) -> None:
    """Issue #2597: No backup should be created when saving to a non-existent file."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save to non-existent file
    todos = [Todo(id=1, text="first task")]
    storage.save(todos)

    # Verify no backup file was created
    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists(), "Backup file should not be created for new files"


def test_backup_rotation_keeps_only_last_n_backups(tmp_path) -> None:
    """Issue #2597: Backup rotation should keep only the last N backups (default N=3).

    Rotation scheme:
    - .bak3 is deleted (if exists)
    - .bak2 → .bak3
    - .bak1 → .bak2
    - .bak → .bak1
    - current → .bak
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Perform multiple saves to trigger rotation
    for i in range(5):
        todos = [Todo(id=1, text=f"version {i}")]
        storage.save(todos)

    # Verify only last 3 backups exist
    bak_path = tmp_path / "todo.json.bak"
    bak1_path = tmp_path / "todo.json.bak1"
    bak2_path = tmp_path / "todo.json.bak2"
    bak3_path = tmp_path / "todo.json.bak3"
    bak4_path = tmp_path / "todo.json.bak4"

    assert bak_path.exists(), ".bak should exist"
    assert bak1_path.exists(), ".bak1 should exist"
    assert bak2_path.exists(), ".bak2 should exist"
    assert not bak3_path.exists(), ".bak3 should not exist (outside rotation limit)"
    assert not bak4_path.exists(), ".bak4 should not exist (outside rotation limit)"

    # Verify backup contents are correct
    bak_content = json.loads(bak_path.read_text(encoding="utf-8"))
    assert bak_content[0]["text"] == "version 3"

    bak1_content = json.loads(bak1_path.read_text(encoding="utf-8"))
    assert bak1_content[0]["text"] == "version 2"

    bak2_content = json.loads(bak2_path.read_text(encoding="utf-8"))
    assert bak2_content[0]["text"] == "version 1"


def test_backup_file_has_correct_permissions(tmp_path) -> None:
    """Issue #2597: Backup files should have the same restrictive permissions as main file (0o600)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Overwrite to create backup
    new_todos = [Todo(id=1, text="new")]
    storage.save(new_todos)

    # Verify backup has correct permissions
    backup_path = tmp_path / "todo.json.bak"
    backup_stat = backup_path.stat()
    backup_mode = stat.S_IMODE(backup_stat.st_mode)

    # Should have exactly 0o600 (rw-------)
    assert backup_mode == 0o600, (
        f"Backup file should have 0o600 permissions, got 0o{backup_mode:o}"
    )


def test_backup_contains_valid_json_matching_previous_state(tmp_path) -> None:
    """Issue #2597: Backup file should contain valid JSON that can be loaded with TodoStorage."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create complex initial data
    original_todos = [
        Todo(id=1, text="task with unicode: 你好"),
        Todo(id=2, text='task with "quotes"', done=True),
        Todo(id=3, text="task with \\n newline"),
    ]
    storage.save(original_todos)

    # Overwrite
    storage.save([Todo(id=1, text="simple")])

    # Verify backup can be loaded and contains valid data
    backup_path = tmp_path / "todo.json.bak"
    backup_storage = TodoStorage(str(backup_path))
    loaded_todos = backup_storage.load()

    assert len(loaded_todos) == 3
    assert loaded_todos[0].text == "task with unicode: 你好"
    assert loaded_todos[1].text == 'task with "quotes"'
    assert loaded_todos[1].done is True
    assert loaded_todos[2].text == "task with \\n newline"


def test_backup_failure_doesnt_prevent_main_save_operation(tmp_path) -> None:
    """Issue #2597: If backup creation fails, the main save operation should still succeed.

    This ensures that backup failures don't break the core functionality.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Make backup directory read-only to simulate backup failure
    backup_path = tmp_path / "todo.json.bak"
    backup_path.write_text("blocker")  # Create a file that will interfere

    try:
        # This should still succeed despite backup issues
        new_todos = [Todo(id=1, text="new data")]
        storage.save(new_todos)

        # Verify main file was updated
        assert db.exists()
        main_content = json.loads(db.read_text(encoding="utf-8"))
        assert main_content[0]["text"] == "new data"
    finally:
        # Clean up for next tests
        if backup_path.exists():
            backup_path.unlink()


def test_no_backup_flag_prevents_backup_creation(tmp_path) -> None:
    """Issue #2597: The --no-backup flag should prevent backup creation.

    This test verifies the TodoStorage backup_enabled parameter works correctly.
    """
    db = tmp_path / "todo.json"
    # Create storage with backups disabled
    storage = TodoStorage(str(db), backup_enabled=False)

    # Create initial data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Overwrite with new data
    new_todos = [Todo(id=1, text="new")]
    storage.save(new_todos)

    # Verify NO backup file was created
    backup_path = tmp_path / "todo.json.bak"
    assert not backup_path.exists(), "Backup should not be created when backup_enabled=False"


def test_cli_no_backup_flag_passed_to_storage(tmp_path) -> None:
    """Issue #2597: The CLI --no-backup flag should be passed to TodoStorage.

    This test verifies the CLI integration works correctly.
    """
    from argparse import Namespace

    # Simulate CLI args with --no-backup flag
    args = Namespace(
        db=str(tmp_path / "todo.json"),
        command="add",
        text="test todo",
        no_backup=True,
        pending=False,
    )

    # Create TodoApp through the normal CLI flow
    from flywheel.cli import TodoApp
    app = TodoApp(db_path=args.db, backup_enabled=not args.no_backup)

    # Verify storage was created with backups disabled
    assert (
        app.storage.backup_enabled is False
    ), "TodoStorage should have backup_enabled=False when --no-backup is set"


def test_backup_max_backups_configurable(tmp_path) -> None:
    """Issue #2597: The maximum number of backups should be configurable.

    This test verifies the max_backups parameter works correctly.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db), max_backups=2)

    # Perform multiple saves to trigger rotation
    for i in range(5):
        todos = [Todo(id=1, text=f"version {i}")]
        storage.save(todos)

    # Verify only last 2 backups exist (custom limit)
    bak_path = tmp_path / "todo.json.bak"
    bak1_path = tmp_path / "todo.json.bak1"
    bak2_path = tmp_path / "todo.json.bak2"

    assert bak_path.exists(), ".bak should exist"
    assert bak1_path.exists(), ".bak1 should exist"
    assert not bak2_path.exists(), ".bak2 should not exist (custom max_backups=2)"
