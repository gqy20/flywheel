"""Test for Issue #760 - Verify FileStorage.__init__ is complete and functional.

This test verifies that FileStorage can be properly initialized with all
documented parameters, confirming that the code is NOT truncated.
"""

import os
import tempfile
from pathlib import Path

from flywheel.storage import FileStorage


def test_filestorage_init_with_default_parameters():
    """Test FileStorage initialization with default parameters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = FileStorage(path=str(storage_path))

        # Verify the storage object is properly initialized
        assert storage.path == storage_path
        assert storage.compression is False
        assert storage.backup_count == 0
        assert storage._cache_enabled is False


def test_filestorage_init_with_all_parameters():
    """Test FileStorage initialization with all parameters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = FileStorage(
            path=str(storage_path),
            compression=True,
            backup_count=5,
            enable_cache=True
        )

        # Verify all parameters are correctly set
        assert storage.compression is True
        assert storage.backup_count == 5
        assert storage._cache_enabled is True
        # Path should have .gz extension when compression is enabled
        assert str(storage.path).endswith('.gz')


def test_filestorage_init_has_complete_docstring():
    """Test that FileStorage.__init__ has a complete docstring."""
    docstring = FileStorage.__init__.__doc__

    # Verify docstring exists and is not truncated
    assert docstring is not None
    assert len(docstring) > 100  # Should be a substantial docstring

    # Verify all parameters are documented
    assert "path:" in docstring
    assert "compression:" in docstring
    assert "backup_count:" in docstring
    assert "enable_cache:" in docstring

    # Verify it's not truncated mid-word
    assert "sto" not in docstring or "storage" in docstring  # Not "Path to the sto"


def test_filestorage_init_creates_parent_directories():
    """Test that FileStorage initialization creates parent directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        nested_path = Path(tmpdir) / "nested" / "dir" / "todos.json"
        storage = FileStorage(path=str(nested_path))

        # Verify parent directory was created
        assert storage.path.parent.exists()
        assert storage.path.parent.is_dir()


def test_filestorage_init_with_tilde_expansion():
    """Test that FileStorage expands tilde in paths."""
    # Get the actual home directory
    home = Path.home()

    # Create a temporary path with tilde
    with tempfile.TemporaryDirectory() as tmpdir:
        rel_path = Path(tmpdir).relative_to(home)
        tilde_path = f"~/{rel_path}/todos.json"

        storage = FileStorage(path=tilde_path)

        # Verify tilde was expanded
        assert storage.path == home / rel_path / "todos.json"
