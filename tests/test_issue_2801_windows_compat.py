"""Regression tests for issue #2801: os.fchmod() is Unix-only and will crash on Windows.

Issue: os.fchmod() is called without platform detection at src/flywheel/storage.py:112.
On Windows, this causes AttributeError because os.fchmod is Unix-only.

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, PropertyMock, patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_missing(tmp_path) -> None:
    """Issue #2801: Save should work even when os.fchmod is not available (Windows).

    Before fix: save() crashes with AttributeError on Windows
    After fix: save() gracefully handles missing os.fchmod

    This simulates Windows behavior where os.fchmod doesn't exist.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test todo")]

    # Create a mock os module without fchmod attribute (simulating Windows)
    import os as real_os

    mock_os = MagicMock(spec=real_os)
    # Copy all attributes from real os except we'll control fchmod
    for attr in dir(real_os):
        if not attr.startswith("_"):
            with contextlib.suppress(AttributeError, TypeError):
                setattr(mock_os, attr, getattr(real_os, attr))

    # Remove fchmod attribute to simulate Windows
    # Use type(mock_os).fchmod = PropertyMock(side_effect=AttributeError) approach
    # The key is to make hasattr(os, 'fchmod') return False
    type(mock_os).fchmod = PropertyMock(side_effect=AttributeError("os has no attribute 'fchmod'"))

    with patch("flywheel.storage.os", mock_os):
        # This should NOT crash on Windows
        storage.save(todos)

    # Verify the save actually worked
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_save_sets_restrictive_permissions_on_unix(tmp_path) -> None:
    """Issue #2801: On Unix systems, temp files should still have restrictive permissions.

    Before fix: os.fchmod is called unconditionally
    After fix: os.fchmod is still called when available (Unix), preserving security

    This verifies the fix doesn't break security on Unix systems.
    """
    import os as os_module
    import stat as stat_module

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="secure todo")]

    # Track if fchmod was called with correct permissions
    fchmod_called = []
    original_fchmod = os_module.fchmod

    def tracking_fchmod(fd, mode):
        fchmod_called.append((fd, mode))
        return original_fchmod(fd, mode)

    with patch("flywheel.storage.os.fchmod", side_effect=tracking_fchmod):
        storage.save(todos)

    # Verify fchmod was called with restrictive permissions (0o600)
    assert len(fchmod_called) == 1, "os.fchmod should have been called once on Unix"
    _fd, mode = fchmod_called[0]
    expected_mode = stat_module.S_IRUSR | stat_module.S_IWUSR  # 0o600
    assert mode == expected_mode, f"Expected mode {oct(expected_mode)}, got {oct(mode)}"

    # Verify save worked
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "secure todo"


def test_windows_compat_preserves_atomicity(tmp_path) -> None:
    """Issue #2801: Windows compatibility fix should not break atomic writes.

    Verifies that even when os.fchmod is missing (Windows scenario),
    the atomic rename pattern still works correctly.
    """
    import os as real_os

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a mock os module without fchmod attribute (simulating Windows)
    mock_os = MagicMock(spec=real_os)
    for attr in dir(real_os):
        if not attr.startswith("_"):
            with contextlib.suppress(AttributeError, TypeError):
                setattr(mock_os, attr, getattr(real_os, attr))

    # Remove fchmod attribute to simulate Windows
    type(mock_os).fchmod = PropertyMock(side_effect=AttributeError("os has no attribute 'fchmod'"))

    with patch("flywheel.storage.os", mock_os):
        # Create initial data
        storage.save([Todo(id=1, text="initial")])

        # Update data
        storage.save([Todo(id=1, text="updated"), Todo(id=2, text="new")])

    # Verify final state is correct
    loaded = storage.load()
    assert len(loaded) == 2
    assert loaded[0].text == "updated"
    assert loaded[1].text == "new"


def test_windows_compat_multiple_saves(tmp_path) -> None:
    """Issue #2801: Multiple saves should work consistently on Windows.

    Tests that the fix handles repeated operations correctly.
    """
    import os as real_os

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create a mock os module without fchmod attribute (simulating Windows)
    mock_os = MagicMock(spec=real_os)
    for attr in dir(real_os):
        if not attr.startswith("_"):
            with contextlib.suppress(AttributeError, TypeError):
                setattr(mock_os, attr, getattr(real_os, attr))

    # Remove fchmod attribute to simulate Windows
    type(mock_os).fchmod = PropertyMock(side_effect=AttributeError("os has no attribute 'fchmod'"))

    with patch("flywheel.storage.os", mock_os):
        for i in range(5):
            storage.save([Todo(id=i, text=f"todo {i}")])
            loaded = storage.load()
            assert len(loaded) == 1
            assert loaded[0].text == f"todo {i}"

    # Final verification
    final_loaded = storage.load()
    assert len(final_loaded) == 1
    assert final_loaded[0].text == "todo 4"
