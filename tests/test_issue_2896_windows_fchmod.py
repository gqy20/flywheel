"""Regression test for issue #2896: os.fchmod not available on Windows.

This test verifies that TodoStorage.save() works correctly on Windows
where os.fchmod is not available.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_without_fchmod_simulating_windows(tmp_path: Path) -> None:
    """Regression test for issue #2896: save() should work on Windows.

    On Windows, os.fchmod does not exist. This test simulates that
    environment by temporarily deleting the fchmod attribute.
    The save() operation should succeed without AttributeError.
    """
    import os

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Save original fchmod if it exists (Unix)
    original_fchmod = getattr(os, "fchmod", None)

    try:
        # Simulate Windows by removing fchmod from os module
        if hasattr(os, "fchmod"):
            delattr(os, "fchmod")

        # Verify fchmod is gone (simulating Windows)
        assert not hasattr(os, "fchmod"), "fchmod should not exist for this test"

        # This should NOT raise AttributeError - the code should handle
        # the missing fchmod gracefully
        storage.save(todos)

        # Verify file was created and contains valid data
        assert db.exists()
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"
    finally:
        # Restore fchmod if it existed originally
        if original_fchmod is not None:
            os.fchmod = original_fchmod  # type: ignore[attr-defined]


def test_save_still_uses_fchmod_on_unix(tmp_path: Path) -> None:
    """Verify that fchmod is still called on Unix where it exists.

    This ensures the fix doesn't accidentally disable fchmod on Unix.
    """
    import os

    # Skip test if fchmod isn't available (we're on Windows)
    if not hasattr(os, "fchmod"):
        pytest.skip("os.fchmod not available on this platform")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="unix test")]

    # Track if fchmod was called
    original_fchmod = os.fchmod
    fchmod_calls = []

    def tracking_fchmod(fd: int, mode: int) -> None:
        fchmod_calls.append((fd, mode))
        return original_fchmod(fd, mode)

    with patch("flywheel.storage.os.fchmod", side_effect=tracking_fchmod):
        storage.save(todos)

    # Verify fchmod was called
    assert len(fchmod_calls) == 1
    # Verify restrictive permissions (0o600 = 0o600)
    import stat

    expected_mode = stat.S_IRUSR | stat.S_IWUSR
    assert fchmod_calls[0][1] == expected_mode

    # Verify file was created correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "unix test"
