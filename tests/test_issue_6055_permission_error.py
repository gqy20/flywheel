"""Regression tests for issue #6055: load() should wrap PermissionError as ValueError.

Issue: load() raises raw PermissionError instead of wrapped ValueError when file is not readable.

When load() is called on a file without read permissions, it should raise ValueError
with a clear message indicating permission was denied, not a raw PermissionError.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from flywheel.storage import TodoStorage


def test_load_raises_valueerror_on_unreadable_file(tmp_path) -> None:
    """Issue #6055: load() should raise ValueError (not PermissionError) for unreadable files.

    Before fix: load() raises raw PermissionError
    After fix: load() raises ValueError with message containing 'permission' or 'denied'
    """
    db = tmp_path / "unreadable.json"

    # Create a valid JSON file first
    db.write_text('[]', encoding="utf-8")

    # Remove read permissions (chmod 0o000)
    os.chmod(db, 0o000)

    try:
        storage = TodoStorage(str(db))

        # Should raise ValueError, not PermissionError
        with pytest.raises(ValueError) as exc_info:
            storage.load()

        # Error message should mention permission or denied
        error_msg = str(exc_info.value).lower()
        assert "permission" in error_msg or "denied" in error_msg, (
            f"Error message should mention 'permission' or 'denied': {exc_info.value}"
        )

    finally:
        # Restore permissions so the file can be cleaned up
        os.chmod(db, 0o600)


def test_load_does_not_raise_permissionerror_on_unreadable_file(tmp_path) -> None:
    """Issue #6055: Verify that PermissionError is not raised directly.

    This test ensures the exception type is ValueError, not PermissionError.
    """
    db = tmp_path / "unreadable2.json"

    # Create a valid JSON file first
    db.write_text('[]', encoding="utf-8")

    # Remove read permissions
    os.chmod(db, 0o000)

    try:
        storage = TodoStorage(str(db))

        # Should NOT raise PermissionError
        with pytest.raises(ValueError):  # ValueError is expected
            storage.load()

        # If we get here without PermissionError, the fix is working

    finally:
        # Restore permissions so the file can be cleaned up
        os.chmod(db, 0o600)
