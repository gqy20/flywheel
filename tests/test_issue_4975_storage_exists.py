"""Regression tests for issue #4975: TodoStorage.exists() helper method."""

import tempfile
from pathlib import Path

from flywheel.storage import TodoStorage


def test_exists_returns_false_before_save():
    """exists() should return False when no database file has been created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_db.json"
        storage = TodoStorage(str(db_path))
        assert storage.exists() is False


def test_exists_returns_true_after_save():
    """exists() should return True after save() has been called."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_db.json"
        storage = TodoStorage(str(db_path))
        assert storage.exists() is False

        storage.save([])  # Save empty list
        assert storage.exists() is True


def test_exists_returns_false_after_delete():
    """exists() should return False if the database file is deleted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_db.json"
        storage = TodoStorage(str(db_path))

        storage.save([])  # Create the file
        assert storage.exists() is True

        db_path.unlink()  # Delete the file
        assert storage.exists() is False
