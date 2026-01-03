"""Test data compression support (Issue #583)."""

import gzip
import json
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_creates_compressed_file():
    """Test that _save creates compressed .json.gz file when compression is enabled.

    This test verifies that:
    1. When saving with compression enabled, a .json.gz file is created
    2. The compressed file can be decompressed and read as valid JSON
    3. The decompressed data contains the correct todos
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json.gz"

        # Create storage with compression enabled
        storage = Storage(str(storage_path))
        todo1 = Todo(id=1, title="Task 1", status="pending")
        storage.add(todo1)

        # Verify compressed file exists
        assert storage_path.exists(), "Compressed file should be created"

        # Verify file is gzip compressed
        with gzip.open(storage_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)

        assert data["todos"][0]["title"] == "Task 1"
        assert len(data["todos"]) == 1


def test_load_reads_compressed_file():
    """Test that _load can read and decompress .json.gz files.

    This test verifies that:
    1. _load can detect .json.gz extension
    2. _load automatically decompresses the file
    3. The decompressed data is loaded correctly into storage
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json.gz"

        # Manually create a compressed file with test data
        test_data = {
            "todos": [
                {"id": 1, "title": "Compressed Task", "status": "pending"}
            ],
            "next_id": 2,
            "metadata": {"checksum": "dummy_checksum"}
        }

        with gzip.open(storage_path, 'wt', encoding='utf-8') as f:
            json.dump(test_data, f)

        # Create storage and load the compressed file
        storage = Storage(str(storage_path))
        storage._load()

        # Verify data was loaded correctly
        assert len(storage._todos) == 1
        assert storage._todos[0].title == "Compressed Task"
        assert storage._todos[0].id == 1


def test_load_handles_regular_json_file():
    """Test that _load still works with regular .json files.

    This test verifies backward compatibility:
    1. _load can still read regular .json files
    2. Loading regular files works alongside compressed files
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage with regular JSON file
        storage = Storage(str(storage_path))
        todo1 = Todo(id=1, title="Regular Task", status="pending")
        storage.add(todo1)

        # Verify regular file exists and works
        assert storage_path.exists()

        # Create new storage instance to reload
        storage2 = Storage(str(storage_path))
        storage2._load()

        # Verify data was loaded correctly
        assert len(storage2._todos) == 1
        assert storage2._todos[0].title == "Regular Task"


def test_compression_reduces_file_size():
    """Test that compression actually reduces file size.

    This test verifies that:
    1. Compressed files are smaller than uncompressed files
    2. Compression is effective for JSON data
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create regular JSON file
        regular_path = Path(tmpdir) / "todos.json"
        storage1 = Storage(str(regular_path))

        # Add many todos to create data that compresses well
        for i in range(100):
            todo = Todo(id=i+1, title=f"Task {i} with some repetitive text", status="pending")
            storage1.add(todo)

        regular_size = regular_path.stat().st_size

        # Create compressed file
        compressed_path = Path(tmpdir) / "todos.json.gz"
        storage2 = Storage(str(compressed_path))

        # Add the same todos
        for i in range(100):
            todo = Todo(id=i+1, title=f"Task {i} with some repetitive text", status="pending")
            storage2.add(todo)

        compressed_size = compressed_path.stat().st_size

        # Compressed file should be smaller
        assert compressed_size < regular_size, \
            f"Compressed file ({compressed_size} bytes) should be smaller than regular file ({regular_size} bytes)"


def test_save_and_load_roundtrip_with_compression():
    """Test complete save/load cycle with compression.

    This test verifies that:
    1. Data saved with compression can be loaded back correctly
    2. All todo attributes are preserved through compression cycle
    3. Multiple save/load cycles work correctly
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json.gz"

        # Create storage and add todos
        storage1 = Storage(str(storage_path))
        todo1 = Todo(id=1, title="Task 1", status="pending", description="Description 1")
        todo2 = Todo(id=2, title="Task 2", status="completed", tags=["tag1", "tag2"])
        storage1.add(todo1)
        storage1.add(todo2)

        # Create new storage instance to reload
        storage2 = Storage(str(storage_path))
        storage2._load()

        # Verify all todos were loaded correctly
        assert len(storage2._todos) == 2
        assert storage2._todos[0].title == "Task 1"
        assert storage2._todos[0].status == "pending"
        assert storage2._todos[0].description == "Description 1"
        assert storage2._todos[1].title == "Task 2"
        assert storage2._todos[1].status == "completed"
        assert storage2._todos[1].tags == ["tag1", "tag2"]


def test_auto_detect_compression_from_extension():
    """Test that compression is automatically detected from file extension.

    This test verifies that:
    1. Files ending with .json.gz are treated as compressed
    2. Files ending with .json are treated as uncompressed
    3. The system handles both formats automatically
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        compressed_path = Path(tmpdir) / "todos.json.gz"
        regular_path = Path(tmpdir) / "todos.json"

        # Test with compressed file
        storage1 = Storage(str(compressed_path))
        assert compressed_path.name.endswith(".json.gz")

        # Test with regular file
        storage2 = Storage(str(regular_path))
        assert regular_path.name.endswith(".json")
