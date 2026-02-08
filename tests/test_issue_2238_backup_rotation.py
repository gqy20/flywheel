"""Tests for backup/rotation support for corrupted database files.

This test suite verifies that TodoStorage creates and rotates backup files
to prevent data loss when JSON is corrupted or contains bugs from successful writes.

Issue: https://github.com/gqy20/flywheel/issues/2238
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestBackupCreation:
    """Test backup creation when saving todos."""

    def test_backup_created_when_file_exists(self, tmp_path) -> None:
        """Test that a backup file is created when overwriting an existing file."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Create initial file
        original_todos = [Todo(id=1, text="original task")]
        storage.save(original_todos)

        # Save new todos - should create backup
        new_todos = [Todo(id=1, text="updated task")]
        storage.save(new_todos)

        # Verify backup was created
        backup_path = tmp_path / "todo.json.bak"
        assert backup_path.exists(), "Backup file should be created"

        # Verify backup contains original data
        backup_storage = TodoStorage(str(backup_path))
        backup_todos = backup_storage.load()
        assert len(backup_todos) == 1
        assert backup_todos[0].text == "original task"

    def test_no_backup_created_for_new_file(self, tmp_path) -> None:
        """Test that no backup is created when file doesn't exist yet."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Save to new file - should NOT create backup
        todos = [Todo(id=1, text="first task")]
        storage.save(todos)

        # Verify no backup was created
        backup_path = tmp_path / "todo.json.bak"
        assert not backup_path.exists(), "No backup should be created for new files"


class TestBackupRotation:
    """Test backup rotation mechanism."""

    def test_backup_rotation_with_keep_backups_3(self, tmp_path) -> None:
        """Test that only N backups are kept when N=3."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), keep_backups=3)

        # Save multiple times to create backups
        for i in range(5):
            todos = [Todo(id=1, text=f"task version {i}")]
            storage.save(todos)

        # Should have main file + 3 backups (.bak, .bak.1, .bak.2)
        assert db.exists(), "Main file should exist"
        assert (tmp_path / "todo.json.bak").exists(), ".bak should exist"
        assert (tmp_path / "todo.json.bak.1").exists(), ".bak.1 should exist"
        assert (tmp_path / "todo.json.bak.2").exists(), ".bak.2 should exist"
        # .bak.3 should NOT exist (only 3 backups kept)
        assert not (tmp_path / "todo.json.bak.3").exists(), ".bak.3 should not exist"

    def test_backup_rotation_ordering(self, tmp_path) -> None:
        """Test that backups are rotated in correct order (.bak -> .bak.1 -> .bak.2)."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), keep_backups=2)

        # Version 0: initial save
        storage.save([Todo(id=1, text="version 0")])

        # Version 1: creates .bak with version 0
        storage.save([Todo(id=1, text="version 1")])
        bak_0_content = (tmp_path / "todo.json.bak").read_text(encoding="utf-8")
        assert "version 0" in bak_0_content

        # Version 2: rotates .bak -> .bak.1, creates new .bak with version 1
        storage.save([Todo(id=1, text="version 2")])
        bak_1_content = (tmp_path / "todo.json.bak.1").read_text(encoding="utf-8")
        bak_current_content = (tmp_path / "todo.json.bak").read_text(encoding="utf-8")
        assert "version 0" in bak_1_content, ".bak.1 should contain version 0"
        assert "version 1" in bak_current_content, ".bak should contain version 1"

    def test_keep_backups_zero_disables_backups(self, tmp_path) -> None:
        """Test that keep_backups=0 disables backup creation."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), keep_backups=0)

        # Initial save
        storage.save([Todo(id=1, text="version 0")])
        # Second save - should NOT create backup
        storage.save([Todo(id=1, text="version 1")])

        # Verify no backups were created
        assert not (tmp_path / "todo.json.bak").exists()
        assert not (tmp_path / "todo.json.bak.1").exists()

    def test_keep_backups_default_is_three(self, tmp_path) -> None:
        """Test that the default keep_backups value is 3."""
        db = tmp_path / "todo.json"
        # Create storage without specifying keep_backups
        storage = TodoStorage(str(db))

        # Verify default is 3
        assert storage.keep_backups == 3, "Default keep_backups should be 3"


class TestListBackups:
    """Test listing available backup files."""

    def test_list_backups_returns_available_backups(self, tmp_path) -> None:
        """Test that list_backups() returns all available backup files."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), keep_backups=3)

        # Create some backups
        for i in range(3):
            storage.save([Todo(id=1, text=f"version {i}")])

        # List backups
        backups = storage.list_backups()

        # Should have 2 backups (after 3 saves: 1st save no backup, 2nd creates .bak, 3rd rotates)
        assert len(backups) >= 1
        # All paths should be under tmp_path
        for backup in backups:
            assert backup.parent == tmp_path
            assert "todo.json.bak" in backup.name

    def test_list_backups_empty_when_no_backups(self, tmp_path) -> None:
        """Test that list_backups() returns empty list when no backups exist."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), keep_backups=3)

        # No saves yet - no backups
        backups = storage.list_backups()
        assert len(backups) == 0

    def test_list_backups_with_keep_backups_zero(self, tmp_path) -> None:
        """Test that list_backups() returns empty when backups are disabled."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), keep_backups=0)

        # Even with saves, no backups should be created
        storage.save([Todo(id=1, text="task")])
        storage.save([Todo(id=1, text="updated task")])

        backups = storage.list_backups()
        assert len(backups) == 0


class TestRestoreFromBackup:
    """Test restoring data from backup files."""

    def test_restore_from_backup_restores_data(self, tmp_path) -> None:
        """Test that restore_from_backup() correctly restores data from backup."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), keep_backups=3)

        # Create initial data and save
        original_todos = [
            Todo(id=1, text="task 1"),
            Todo(id=2, text="task 2", done=True),
        ]
        storage.save(original_todos)

        # Modify and save again (creates backup)
        storage.save([Todo(id=3, text="corrupted data")])

        # Get the backup file
        backups = storage.list_backups()
        assert len(backups) >= 1

        # Restore from backup
        storage.restore_from_backup(backups[0])

        # Verify data was restored
        restored_todos = storage.load()
        assert len(restored_todos) == 2
        assert restored_todos[0].text == "task 1"
        assert restored_todos[1].text == "task 2"
        assert restored_todos[1].done is True

    def test_restore_from_nonexistent_backup_raises_error(self, tmp_path) -> None:
        """Test that restoring from non-existent backup raises an error."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), keep_backups=3)

        # Try to restore from non-existent backup
        fake_backup = tmp_path / "todo.json.bak.nonexistent"

        with pytest.raises(FileNotFoundError, match="Backup file not found"):
            storage.restore_from_backup(fake_backup)

    def test_restore_from_backup_with_invalid_json_raises_error(self, tmp_path) -> None:
        """Test that restoring from corrupted backup raises an appropriate error."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), keep_backups=3)

        # Create a corrupted backup file
        corrupted_backup = tmp_path / "todo.json.bak"
        corrupted_backup.write_text("{ invalid json", encoding="utf-8")

        # Try to restore - should raise ValueError (from JSON decode error)
        with pytest.raises(ValueError, match="Invalid JSON"):
            storage.restore_from_backup(corrupted_backup)


class TestBackupsWithConcurrentAccess:
    """Test that backup mechanism works correctly with concurrent access."""

    def test_backups_preserved_with_concurrent_saves(self, tmp_path) -> None:
        """Test that backups are not corrupted by concurrent saves."""
        import multiprocessing
        import time

        db = tmp_path / "concurrent.json"

        def save_worker(worker_id: int, result_queue: multiprocessing.Queue) -> None:
            """Worker function that saves todos and reports success."""
            try:
                storage = TodoStorage(str(db), keep_backups=2)
                todos = [
                    Todo(id=1, text=f"worker-{worker_id}-todo-1"),
                    Todo(id=2, text=f"worker-{worker_id}-todo-2"),
                ]
                storage.save(todos)

                # Small delay to increase race condition likelihood
                time.sleep(0.001)

                # Verify we can read back valid data
                loaded = storage.load()
                result_queue.put(("success", worker_id, len(loaded)))
            except Exception as e:
                result_queue.put(("error", worker_id, str(e)))

        # Run multiple workers concurrently
        num_workers = 3
        processes = []
        result_queue = multiprocessing.Queue()

        for i in range(num_workers):
            p = multiprocessing.Process(target=save_worker, args=(i, result_queue))
            processes.append(p)
            p.start()

        # Wait for all processes to complete
        for p in processes:
            p.join(timeout=10)

        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # All workers should have succeeded without errors
        errors = [r for r in results if r[0] == "error"]
        assert len(errors) == 0, f"Workers encountered errors: {errors}"

        # Verify at least one valid backup exists
        storage = TodoStorage(str(db), keep_backups=2)
        backups = storage.list_backups()

        # Even with concurrent access, we should have valid backups
        for backup in backups:
            # Each backup should be valid JSON
            backup_content = backup.read_text(encoding="utf-8")
            import json
            json.loads(backup_content)  # Should not raise
