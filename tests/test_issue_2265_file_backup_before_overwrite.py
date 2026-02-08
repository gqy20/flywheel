"""Tests for file backup before overwrite functionality (Issue #2265).

This test suite verifies that TodoStorage.save() creates backup files
before overwriting the main data file, providing a recovery mechanism
in case of data corruption or incorrect saves.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestFileBackupBeforeOverwrite:
    """Test suite for issue #2265: Add file backup before overwrite."""

    def test_backup_file_created_when_enabled(self, tmp_path) -> None:
        """Test that .backup file is created when enable_backup=True."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), enable_backup=True)

        # Create initial data
        original_todos = [Todo(id=1, text="original data")]
        storage.save(original_todos)

        # Save new data - this should create a backup
        new_todos = [Todo(id=1, text="new data")]
        storage.save(new_todos)

        # Verify backup file exists
        backup_path = tmp_path / "todo.json.backup"
        assert backup_path.exists(), "Backup file should be created when enable_backup=True"

        # Verify backup contains original data
        backup_storage = TodoStorage(str(backup_path))
        backup_todos = backup_storage.load()
        assert len(backup_todos) == 1
        assert backup_todos[0].text == "original data"

    def test_no_backup_created_when_disabled(self, tmp_path) -> None:
        """Test that no backup file is created when enable_backup=False."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), enable_backup=False)

        # Create initial data
        original_todos = [Todo(id=1, text="original data")]
        storage.save(original_todos)

        # Save new data - should NOT create a backup
        new_todos = [Todo(id=1, text="new data")]
        storage.save(new_todos)

        # Verify no backup file exists
        backup_path = tmp_path / "todo.json.backup"
        assert not backup_path.exists(), "Backup file should not be created when enable_backup=False"

    def test_max_backups_limits_retained_backups(self, tmp_path) -> None:
        """Test that max_backups parameter controls number of retained backups."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), enable_backup=True, max_backups=2)

        # Create initial data
        storage.save([Todo(id=1, text="v1")])

        # Save multiple times - should only keep max_backups=2
        for i in range(5):
            storage.save([Todo(id=1, text=f"v{i+2}")])

        # Check that only max_backups+1 backups exist (including current backup)
        backup_files = list(tmp_path.glob("todo.json.backup*"))
        # With max_backups=2, we should have: .backup (latest) and .backup.1 (second latest)
        assert len(backup_files) <= 2, f"Should have at most 2 backups, found {len(backup_files)}"

    def test_max_backups_equals_one_keeps_single_backup(self, tmp_path) -> None:
        """Test that max_backups=1 keeps only the most recent backup."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), enable_backup=True, max_backups=1)

        # Create initial data
        storage.save([Todo(id=1, text="original")])

        # Save multiple times
        for i in range(3):
            storage.save([Todo(id=1, text=f"version{i+1}")])

        # Should only have one backup file
        backup_files = list(tmp_path.glob("todo.json.backup*"))
        assert len(backup_files) == 1, "Should have exactly 1 backup when max_backups=1"

        # The backup should contain the data before the last save
        backup_path = tmp_path / "todo.json.backup"
        backup_storage = TodoStorage(str(backup_path))
        backup_todos = backup_storage.load()
        # Before saving "version2", we had "version1"
        # Before saving "version3", we had "version2"
        # The final backup should have "version2" (data before last save)
        assert backup_todos[0].text == "version2"

    def test_backup_failure_does_not_prevent_main_save(self, tmp_path) -> None:
        """Test that backup failure does not prevent the main save operation."""
        db = tmp_path / "todo.json"

        # Create initial data
        initial_todos = [Todo(id=1, text="original data")]
        storage = TodoStorage(str(db), enable_backup=True)
        storage.save(initial_todos)

        # Make backup directory read-only to simulate backup failure
        backup_path = tmp_path / "todo.json.backup"

        # Create a directory with the same name as our backup file
        # This will cause the backup copy to fail
        backup_path.mkdir()

        # Save should still succeed even though backup fails
        new_todos = [Todo(id=1, text="new data")]
        storage.save(new_todos)  # Should not raise

        # Verify main file was updated despite backup failure
        main_storage = TodoStorage(str(db))
        loaded_todos = main_storage.load()
        assert len(loaded_todos) == 1
        assert loaded_todos[0].text == "new data"

    def test_backup_not_created_on_first_save(self, tmp_path) -> None:
        """Test that backup is not created when file doesn't exist yet."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), enable_backup=True)

        # First save - no existing file to backup
        storage.save([Todo(id=1, text="first data")])

        # Verify no backup file was created
        backup_path = tmp_path / "todo.json.backup"
        assert not backup_path.exists(), "No backup should be created on first save (no existing file)"

    def test_backup_rotation_removes_oldest(self, tmp_path) -> None:
        """Test that backup rotation removes oldest backups when limit is exceeded."""
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db), enable_backup=True, max_backups=3)

        # Create initial state
        storage.save([Todo(id=1, text="v0")])

        # Create 5 saves to exceed max_backups
        expected_versions = []
        for i in range(1, 6):  # v1 through v5
            storage.save([Todo(id=1, text=f"v{i}")])
            expected_versions.append(f"v{i}")

        # Should have at most max_backups backup files
        backup_files = sorted(tmp_path.glob("todo.json.backup*"))
        assert len(backup_files) <= 3, f"Should have at most 3 backups, found {len(backup_files)}"
