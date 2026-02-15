"""Regression test for issue #3462: os.fchmod not available on Windows.

This test verifies that TodoStorage.save() works on platforms where
os.fchmod is not available (e.g., Windows).
"""

from __future__ import annotations

import os
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_unavailable(tmp_path) -> None:
    """Test that save() works when os.fchmod is not available (Windows scenario).

    On Windows, os.fchmod raises AttributeError. This test mocks that behavior
    to verify the code handles this gracefully without breaking.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Mock os.fchmod to raise AttributeError as on Windows
    def mock_fchmod(*args, **kwargs):
        raise AttributeError("module 'os' has no attribute 'fchmod'")

    with patch.object(os, "fchmod", mock_fchmod, create=True):
        # This should NOT raise AttributeError
        todos = [Todo(id=1, text="test todo")]
        storage.save(todos)

    # Verify the file was saved correctly
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_save_fchmod_missing_attribute(tmp_path) -> None:
    """Test that save() works when os.fchmod attribute doesn't exist.

    Simulates the exact Windows scenario where os.fchmod is missing entirely.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    original_fchmod = getattr(os, "fchmod", None)

    # Remove fchmod temporarily (simulate Windows)
    if hasattr(os, "fchmod"):
        delattr(os, "fchmod")

    try:
        todos = [Todo(id=1, text="windows compatible save")]
        # Should not raise AttributeError
        storage.save(todos)

        # Verify content
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "windows compatible save"
    finally:
        # Restore fchmod if it existed
        if original_fchmod is not None:
            os.fchmod = original_fchmod
