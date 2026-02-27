"""Tests for PermissionError wrapping in TodoStorage.load() (Issue #6055).

This test suite verifies that:
1. PermissionError from unreadable files is wrapped as ValueError
2. Error message indicates permission was denied
"""

from __future__ import annotations

import os

import pytest

from flywheel.storage import TodoStorage


def test_load_wraps_permission_error_as_value_error(tmp_path) -> None:
    """When file is not readable, load() should raise ValueError, not PermissionError."""
    db = tmp_path / "unreadable.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    db.write_text('[{"id": 1, "text": "task"}]', encoding="utf-8")

    # Remove read permissions
    os.chmod(db, 0o000)

    try:
        # Should raise ValueError (not PermissionError)
        with pytest.raises(ValueError, match=r"permission|denied|read"):
            storage.load()
    finally:
        # Restore permissions for cleanup
        os.chmod(db, 0o644)


def test_load_permission_error_message_contains_path(tmp_path) -> None:
    """Error message should contain the file path for context."""
    db = tmp_path / "no_access.json"
    storage = TodoStorage(str(db))

    # Create a valid JSON file
    db.write_text('[{"id": 1, "text": "task"}]', encoding="utf-8")

    # Remove read permissions
    os.chmod(db, 0o000)

    try:
        # Error message should mention the file path
        with pytest.raises(ValueError, match=str(db)):
            storage.load()
    finally:
        # Restore permissions for cleanup
        os.chmod(db, 0o644)
