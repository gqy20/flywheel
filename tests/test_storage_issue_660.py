"""Test that FileStorage implements all abstract methods from AbstractStorage (Issue #660).

This test verifies that the FileStorage class is complete and properly implements
all abstract methods required by the AbstractStorage base class.
"""

import inspect
from abc import ABC
from flywheel.storage import FileStorage, AbstractStorage


def test_filestorage_implements_all_abstract_methods():
    """Test that FileStorage implements all AbstractStorage abstract methods."""
    # Get all abstract methods from AbstractStorage
    abstract_methods = AbstractStorage.__abstractmethods__

    # Verify that FileStorage implements all of them
    for method_name in abstract_methods:
        # Check if the method exists in FileStorage
        assert hasattr(FileStorage, method_name), (
            f"FileStorage missing abstract method: {method_name}"
        )

        # Check that it's actually implemented (not abstract)
        method = getattr(FileStorage, method_name)
        assert not getattr(method, "__isabstractmethod__", False), (
            f"FileStorage.{method_name} is still abstract"
        )

        # Verify it's a concrete method
        assert callable(method), f"FileStorage.{method_name} is not callable"


def test_filestorage_init_is_complete():
    """Test that FileStorage.__init__ method is complete and properly closed."""
    # Check that __init__ exists and is callable
    assert hasattr(FileStorage, "__init__")
    assert callable(FileStorage.__init__)

    # Get the source code of __init__
    source = inspect.getsource(FileStorage.__init__)

    # Basic sanity checks for completeness
    assert "def __init__" in source
    assert "self" in source
    # The method should be properly indented and have a body
    lines = source.split("\n")
    assert len(lines) > 1, "__init__ should have more than just the def line"


def test_filestorage_has_required_methods():
    """Test that FileStorage has all the methods mentioned in the issue."""
    required_methods = [
        "add",
        "list",
        "get",
        "update",
        "delete",
        "get_next_id",
        "add_batch",
        "update_batch",
    ]

    for method_name in required_methods:
        assert hasattr(FileStorage, method_name), (
            f"FileStorage missing required method: {method_name}"
        )
        method = getattr(FileStorage, method_name)
        assert callable(method), f"FileStorage.{method_name} is not callable"


def test_filestorage_is_concrete():
    """Test that FileStorage can be instantiated (is not abstract)."""
    # FileStorage should be instantiable
    # This will fail if FileStorage is still abstract
    import tempfile
    import os

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_path = f.name

    try:
        # This should not raise TypeError about abstract methods
        storage = FileStorage(path=temp_path)
        assert storage is not None
        assert isinstance(storage, AbstractStorage)
        assert isinstance(storage, FileStorage)
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_filestorage_comment_not_truncated():
    """Test that the comment at line 261 is complete (Issue #660)."""
    # Read the storage.py file
    from pathlib import Path

    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    source_code = storage_path.read_text()

    # Check that the comment is complete
    # The issue reported it was truncated as "Track initialization success to co"
    # but it should be "Track initialization success to control cleanup registration"
    assert "Track initialization success to control cleanup registration" in source_code, (
        "Comment appears to be truncated. "
        "Expected 'Track initialization success to control cleanup registration'"
    )
