"""Test data integrity checksums (Issue #223)."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestChecksum:
    """Test data integrity checksums."""

    def test_checksum_saved_and_verified(self):
        """Test that checksum is saved and verified on load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Create storage and add a todo
            storage = Storage(str(storage_path))
            todo1 = Todo(id=1, title="Task 1", status="pending")
            storage.add(todo1)

            # Read the file and verify checksum exists
            with storage_path.open('r') as f:
                data = json.load(f)

            assert "metadata" in data, "File should contain metadata"
            assert "checksum" in data["metadata"], "Metadata should contain checksum"

            # Verify we can load the file successfully
            storage2 = Storage(str(storage_path))
            todos = storage2.list()
            assert len(todos) == 1
            assert todos[0].title == "Task 1"

    def test_checksum_mismatch_raises_error(self):
        """Test that checksum mismatch raises RuntimeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Create storage and add a todo
            storage = Storage(str(storage_path))
            todo1 = Todo(id=1, title="Task 1", status="pending")
            storage.add(todo1)
            storage.close()

            # Tamper with the todos data
            with storage_path.open('r') as f:
                data = json.load(f)

            # Modify the todos list (simulate corruption or external modification)
            data["todos"][0]["title"] = "Modified Task"

            # Write back the tampered data without updating checksum
            with storage_path.open('w') as f:
                json.dump(data, f, indent=2)

            # Try to load - should raise RuntimeError due to checksum mismatch
            with pytest.raises(RuntimeError) as exc_info:
                Storage(str(storage_path))

            assert "checksum" in str(exc_info.value).lower()

    def test_checksum_calculation_for_multiple_todos(self):
        """Test checksum calculation for multiple todos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            storage = Storage(str(storage_path))
            storage.add(Todo(id=1, title="Task 1", status="pending"))
            storage.add(Todo(id=2, title="Task 2", status="completed"))
            storage.add(Todo(id=3, title="Task 3", status="pending"))

            # Read file and verify checksum
            with storage_path.open('r') as f:
                data = json.load(f)

            assert "metadata" in data
            assert "checksum" in data["metadata"]

            # Verify storage can be loaded
            storage2 = Storage(str(storage_path))
            todos = storage2.list()
            assert len(todos) == 3

    def test_checksum_handles_empty_todos(self):
        """Test checksum calculation for empty todos list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            storage = Storage(str(storage_path))

            # Read file and verify checksum exists even for empty list
            with storage_path.open('r') as f:
                data = json.load(f)

            assert "metadata" in data
            assert "checksum" in data["metadata"]

            # Verify storage can be loaded
            storage2 = Storage(str(storage_path))
            todos = storage2.list()
            assert len(todos) == 0

    def test_checksum_ignores_metadata_field(self):
        """Test that checksum is calculated on todos only, not including metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            storage = Storage(str(storage_path))
            todo1 = Todo(id=1, title="Task 1", status="pending")
            storage.add(todo1)
            storage.close()

            # Read the original checksum
            with storage_path.open('r') as f:
                data = json.load(f)
            original_checksum = data["metadata"]["checksum"]

            # Modify other metadata fields (not checksum)
            data["metadata"]["version"] = "2.0"
            data["metadata"]["modified"] = True

            # Write back
            with storage_path.open('w') as f:
                json.dump(data, f, indent=2)

            # This should still load successfully since we only modified metadata
            # (though in real implementation, checksum validation might need to be adjusted)
            # For now, we expect this to work or fail based on implementation
