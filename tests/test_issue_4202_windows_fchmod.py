"""Tests for issue #4202: Windows compatibility for os.fchmod.

This test suite verifies that TodoStorage.save() works correctly on Windows
where os.fchmod is not available.

Regression test for: https://github.com/gqy20/flywheel/issues/4202
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_without_fchmod_simulating_windows(tmp_path) -> None:
    """Test that save() works when os.fchmod is not available (Windows).

    Simulates Windows environment where os.fchmod doesn't exist by
    temporarily removing the attribute and verifying save() still works.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Store original fchmod value (may be None on Windows)
    original_fchmod = getattr(os, "fchmod", None)

    # Simulate Windows by removing os.fchmod
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        # This should NOT raise AttributeError
        storage.save(todos)

        # Verify the file was written correctly
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test todo"
    finally:
        # Restore original state
        if original_fchmod is not None:
            os.fchmod = original_fchmod


def test_save_uses_fchmod_when_available_on_posix(tmp_path) -> None:
    """Test that save() sets permissions correctly when fchmod is available.

    On POSIX systems, the code should use fchmod to set restrictive permissions.
    This test verifies the code path is exercised when fchmod exists.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Track if fchmod was called
    fchmod_called = []
    original_fchmod = getattr(os, "fchmod", None)

    if original_fchmod is None:
        # On Windows, skip the fchmod call verification
        pytest.skip("os.fchmod not available on this platform")

    def tracking_fchmod(fd, mode):
        fchmod_called.append((fd, mode))
        return original_fchmod(fd, mode)

    with patch.object(os, "fchmod", tracking_fchmod):
        storage.save(todos)

    # Verify fchmod was called with the correct mode (0o600)
    assert len(fchmod_called) == 1
    assert fchmod_called[0][1] == 0o600  # S_IRUSR | S_IWUSR

    # Verify the file was written correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_save_without_fchmod_still_creates_valid_json(tmp_path) -> None:
    """Test that save() creates valid JSON even when fchmod is not available."""
    import json

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first todo"),
        Todo(id=2, text="second todo", done=True),
    ]

    # Store original fchmod value
    original_fchmod = getattr(os, "fchmod", None)

    # Simulate Windows by removing os.fchmod
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        storage.save(todos)

        # Verify file contains valid JSON
        raw_content = db.read_text(encoding="utf-8")
        parsed = json.loads(raw_content)

        assert len(parsed) == 2
        assert parsed[0]["text"] == "first todo"
        assert parsed[1]["text"] == "second todo"
        assert parsed[1]["done"] is True
    finally:
        # Restore original state
        if original_fchmod is not None:
            os.fchmod = original_fchmod
