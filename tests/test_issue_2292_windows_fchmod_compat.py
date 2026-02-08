"""Regression test for issue #2292: os.fchmod() is Unix-only, will crash on Windows.

os.fchmod() is only available on Unix and will raise AttributeError on Windows.
This test verifies that TodoStorage.save() works on Windows platforms.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_on_windows_without_attributeerror(tmp_path) -> None:
    """Test that save() works on Windows without AttributeError from os.fchmod.

    os.fchmod() is only available on Unix. This test mocks Windows platform
    and verifies save() works correctly.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo on Windows")]

    # Mock Windows platform where os.fchmod doesn't exist
    with patch("flywheel.storage.os.fchmod", side_effect=AttributeError("fchmod not on Windows")):
        # This should NOT raise AttributeError
        storage.save(todos)

    # Verify the file was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo on Windows"


def test_fchmod_not_called_on_windows_platform(tmp_path) -> None:
    """Test that os.fchmod is not called when sys.platform is win32."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Mock sys.platform to simulate Windows
    with patch("sys.platform", "win32"):
        # Create a mock that would raise AttributeError if called
        mock_fchmod = MagicMock(side_effect=AttributeError("fchmod not available"))
        with patch("flywheel.storage.os.fchmod", mock_fchmod):
            # This should work without calling fchmod
            storage.save(todos)

    # Verify fchmod was not called on Windows
    mock_fchmod.assert_not_called()

    # Verify the file was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_temp_file_has_restrictive_permissions_on_unix(tmp_path, monkeypatch) -> None:
    """Test that temp file has restrictive permissions (0o600) on Unix.

    On Unix, temp files should have owner-only read/write permissions.
    On Windows, file permissions work differently and this is not applicable.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="secure todo")]

    # Only run this test on Unix platforms
    import sys
    if sys.platform == "win32":
        pytest.skip("File permissions work differently on Windows")

    import stat

    # Save the todos
    storage.save(todos)

    # Verify the target file has restrictive permissions
    # Note: After chmod and rename, the final file should have restrictive permissions
    db_stat = db.stat()
    # Check that file is not world-readable or world-writable
    # (permissions should be 0o600 or more restrictive)
    assert not (db_stat.st_mode & stat.S_IROTH)  # No world read
    assert not (db_stat.st_mode & stat.S_IWOTH)  # No world write
