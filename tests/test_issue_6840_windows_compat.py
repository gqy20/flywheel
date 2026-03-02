"""Regression tests for issue #6840: os.fchmod is Unix-only.

Issue: os.fchmod raises AttributeError on Windows because it only exists on Unix.
The code should gracefully handle platforms where os.fchmod is unavailable.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_unavailable(tmp_path) -> None:
    """Issue #6840: save() should work without os.fchmod on Windows.

    Before fix: save() raises AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() works gracefully, skipping permission setting on Windows
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows environment where os.fchmod doesn't exist
    # Create a mock os module without fchmod
    mock_os = type(os)('os')
    for attr in dir(os):
        if not attr.startswith('_') and hasattr(os, attr):
            setattr(mock_os, attr, getattr(os, attr))
    # Explicitly remove fchmod to simulate Windows
    if hasattr(mock_os, 'fchmod'):
        delattr(mock_os, 'fchmod')

    with patch('flywheel.storage.os', mock_os):
        # This should NOT raise AttributeError
        storage.save([Todo(id=1, text="test task")])

    # Verify file was created correctly
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test task"


def test_save_works_with_hasattr_fchmod_false(tmp_path) -> None:
    """Issue #6840: Alternative test using hasattr check simulation.

    This test verifies that the code properly guards os.fchmod with a check.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track whether hasattr check is performed
    hasattr_calls = []
    original_hasattr = hasattr

    def tracking_hasattr(obj, name):
        if name == 'fchmod':
            hasattr_calls.append(name)
            return False  # Simulate fchmod not available
        return original_hasattr(obj, name)

    # Patch hasattr in the storage module
    with patch('builtins.hasattr', tracking_hasattr):
        # This should work without calling fchmod
        storage.save([Todo(id=1, text="windows compatible")])

    # Verify the hasattr check was performed for fchmod
    assert 'fchmod' in hasattr_calls, "Code should check hasattr(os, 'fchmod')"

    # Verify file was created
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "windows compatible"


def test_fchmod_not_called_on_windows_simulation(tmp_path) -> None:
    """Issue #6840: Verify os.fchmod is NOT called when unavailable.

    If the fix is correct, os.fchmod should never be called on Windows.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a mock os module WITHOUT fchmod (simulating Windows)
    class MockOS:
        """Mock os module that simulates Windows (no fchmod)."""

        # Copy necessary attributes from os
        fdopen = staticmethod(os.fdopen)
        replace = staticmethod(os.replace)
        unlink = staticmethod(os.unlink)
        O_EXCL = os.O_EXCL if hasattr(os, 'O_EXCL') else 0

        # Intentionally NOT defining fchmod - this simulates Windows

    # tempfile.mkstemp needs to work
    import flywheel.storage as storage_module

    with patch.object(storage_module, 'os', MockOS):
        # This should NOT call fchmod since hasattr check will return False
        storage.save([Todo(id=1, text="no fchmod call")])

    # Verify file was created successfully
    assert db.exists()
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "no fchmod call"
