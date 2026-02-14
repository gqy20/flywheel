"""Regression test for issue #3310: os.fchmod Unix-only compatibility.

os.fchmod is only available on Unix platforms and will raise AttributeError on Windows.
This test verifies that save() works gracefully on platforms without os.fchmod.
"""

from __future__ import annotations

import builtins
import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_handles_missing_fchmod_gracefully(tmp_path: Path) -> None:
    """Test that save() works without error when os.fchmod is not available.

    This simulates Windows platform behavior where os.fchmod is not present.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Save original hasattr
    original_hasattr = builtins.hasattr

    # Mock hasattr to return False for os.fchmod (simulating Windows)
    def mock_hasattr(obj, name):
        if obj is os and name == "fchmod":
            return False
        return original_hasattr(obj, name)

    with patch("builtins.hasattr", mock_hasattr):
        # This should NOT raise an error - the fchmod is skipped gracefully
        storage.save(todos)

    # Verify the file was still saved correctly
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_save_sets_restrictive_permissions_on_unix(tmp_path: Path) -> None:
    """Test that save() sets restrictive permissions (0o600) on Unix platforms.

    This test verifies that when os.fchmod is available, it is used correctly.
    """
    # Skip test on platforms without fchmod (e.g., Windows)
    if not hasattr(os, "fchmod"):
        pytest.skip("os.fchmod not available on this platform")

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Track whether fchmod was called with correct mode
    fchmod_calls = []

    def track_fchmod(fd: int, mode: int) -> None:
        fchmod_calls.append((fd, mode))

    with patch("flywheel.storage.os.fchmod", track_fchmod):
        storage.save(todos)

    # Verify fchmod was called with correct restrictive mode (0o600)
    assert len(fchmod_calls) == 1
    assert fchmod_calls[0][1] == stat.S_IRUSR | stat.S_IWUSR  # 0o600
