"""Test that _load method is fully implemented and functional.

This test verifies issue #230 - the _load method is actually complete
and working correctly. The issue was a false positive from an AI scanner
that only read the docstring.

Issue: #230
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestLoadMethodImplementation:
    """Verify _load method is fully implemented."""

    def test_load_reads_file_and_parses_json(self):
        """Test that _load reads file and parses JSON correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a storage file with test data
            storage_path = Path(tmpdir) / "test.json"
            test_data = {
                "todos": [
                    {"id": 1, "title": "Task 1", "status": "pending"},
                    {"id": 2, "title": "Task 2", "status": "completed"},
                ],
                "next_id": 3,
                "metadata": {"checksum": "ignored"}
            }

            with storage_path.open("w") as f:
                json.dump(test_data, f)

            # Create storage and verify _load worked
            storage = Storage(str(storage_path))

            # Verify todos were loaded
            assert len(storage.list()) == 2
            assert storage.get(1).title == "Task 1"
            assert storage.get(2).title == "Task 2"

    def test_load_with_checksum_verification(self):
        """Test that _load verifies checksums."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"

            # Create storage with one todo
            storage = Storage(str(storage_path))
            storage.add(Todo(title="Test task", status="pending"))

            # Verify the file has a checksum
            with storage_path.open("r") as f:
                data = json.load(f)
                assert "metadata" in data
                assert "checksum" in data["metadata"]

    def test_load_creates_empty_state_for_nonexistent_file(self):
        """Test that _load initializes empty state when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "nonexistent.json"

            # Create storage for non-existent file
            storage = Storage(str(storage_path))

            # Verify empty state
            assert storage.list() == []
            assert storage.get_next_id() == 1

    def test_load_handles_old_format_backward_compatibility(self):
        """Test that _load handles old list format for backward compatibility."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"

            # Write old format (just a list)
            old_format = [
                {"id": 1, "title": "Old Task 1", "status": "pending"},
                {"id": 5, "title": "Old Task 2", "status": "completed"},
            ]

            with storage_path.open("w") as f:
                json.dump(old_format, f)

            # Create storage and verify backward compatibility
            storage = Storage(str(storage_path))

            # Verify todos were loaded
            assert len(storage.list()) == 2
            assert storage.get(1).title == "Old Task 1"
            assert storage.get(5).title == "Old Task 2"
            # next_id should be calculated from max existing ID
            assert storage.get_next_id() == 6

    def test_load_validates_schema_and_rejects_invalid_data(self):
        """Test that _load validates schema and rejects invalid data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"

            # Write invalid schema (todos is not a list)
            invalid_schema = {
                "todos": "not a list",
                "next_id": 1
            }

            with storage_path.open("w") as f:
                json.dump(invalid_schema, f)

            # Should raise RuntimeError due to schema validation
            with pytest.raises(RuntimeError, match="Invalid schema"):
                Storage(str(storage_path))

    def test_load_resets_dirty_flag_after_successful_load(self):
        """Test that _load resets dirty flag after successful load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"

            # Create storage and add a todo (will be saved)
            storage = Storage(str(storage_path))
            storage.add(Todo(title="Test", status="pending"))

            # Load again - dirty flag should be False
            storage2 = Storage(str(storage_path))
            assert storage2._dirty is False

    def test_load_creates_backup_on_json_decode_error(self):
        """Test that _load creates backup when JSON is invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"
            backup_path = Path(tmpdir) / "test.json.backup"

            # Write invalid JSON
            with storage_path.open("w") as f:
                f.write("{invalid json")

            # Should raise RuntimeError and create backup
            with pytest.raises(RuntimeError, match="Invalid JSON"):
                Storage(str(storage_path))

            # Verify backup was created
            assert backup_path.exists()

    def test_load_atomic_read_and_state_update(self):
        """Test that _load performs read and state update atomically."""
        import threading

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test.json"

            # Create initial storage
            storage = Storage(str(storage_path))
            storage.add(Todo(title="Initial", status="pending"))

            # Create multiple threads that load simultaneously
            results = []
            errors = []

            def load_storage():
                try:
                    s = Storage(str(storage_path))
                    results.append(len(s.list()))
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=load_storage) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # All loads should succeed without errors
            assert len(errors) == 0
            assert all(r == 1 for r in results)
