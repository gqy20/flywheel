"""Regression tests for issue #3544: os.fchmod() is not available on Windows.

Issue: os.fchmod() is a Unix-only function that raises AttributeError on Windows.
The save() method in TodoStorage fails on Windows because of this.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_not_available(tmp_path) -> None:
    """Issue #3544: save() should work on Windows where os.fchmod is not available.

    On Windows, os.fchmod does not exist (raises AttributeError).
    The save() method should gracefully handle this and still complete successfully.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows by making os.fchmod raise AttributeError
    # This is what happens on Windows when you try to use os.fchmod

    def raising_fchmod(*args, **kwargs):
        raise AttributeError("module 'os' has no attribute 'fchmod'")

    import os

    with patch.object(os, "fchmod", raising_fchmod):
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test task")])

    # Verify the file was written successfully
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test task"


def test_save_gracefully_skips_permissions_on_attribute_error(tmp_path) -> None:
    """Issue #3544: save() should gracefully skip permission setting on Windows.

    When os.fchmod raises AttributeError, the save should still succeed,
    just without setting the Unix-style permissions.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    import os

    # Mock fchmod to raise AttributeError (Windows behavior)
    with patch.object(os, "fchmod", side_effect=AttributeError("no fchmod")):
        # Should complete without error
        storage.save([Todo(id=1, text="windows test")])

    # Verify file exists and content is correct
    assert db.exists()
    content = db.read_text(encoding="utf-8")
    assert "windows test" in content
