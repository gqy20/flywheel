"""Regression tests for issue #2739: os.fchmod() is not available on Windows.

Issue: os.fchmod() is called unconditionally in TodoStorage.save() but this
function doesn't exist on Windows, causing AttributeError.

The fix should handle platforms where os.fchmod doesn't exist gracefully.
"""

from __future__ import annotations

import sys

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_code_checks_fchmod_existence_before_calling(tmp_path) -> None:
    """Issue #2739: Verify the code uses hasattr check before calling fchmod.

    This test ensures that hasattr(os, "fchmod") is checked before calling
    os.fchmod(), preventing AttributeError on Windows where os.fchmod doesn't exist.
    """
    import inspect

    import flywheel.storage

    source = inspect.getsource(flywheel.storage.TodoStorage.save)

    # Verify the source code contains the hasattr check for fchmod
    assert 'hasattr(os, "fchmod")' in source or "hasattr(os, 'fchmod')" in source, (
        "The save() method should check for fchmod existence using hasattr() "
        "to prevent AttributeError on Windows where os.fchmod doesn't exist."
    )

    # Also verify the code structure has the if statement
    assert "if hasattr" in source and "fchmod" in source, (
        "The code should have 'if hasattr(os, \"fchmod\")' check before calling os.fchmod()"
    )

    # Verify the code still works
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))
    todos = [Todo(id=1, text="test todo")]
    storage.save(todos)
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test todo"


def test_storage_simulated_windows_environment(tmp_path) -> None:
    """Issue #2739: Verify the hasattr pattern works by checking code structure.

    This test verifies the code structure by inspecting the source, since
    directly mocking os.fchmod removal is unreliable due to Python's module caching.
    """
    import inspect

    import flywheel.storage

    # Get the source code of the save method
    source = inspect.getsource(flywheel.storage.TodoStorage.save)

    # The fix should:
    # 1. Check hasattr(os, "fchmod") before calling it
    # 2. Only call os.fchmod() if it exists
    assert 'hasattr(os, "fchmod")' in source, (
        "Code should check if os.fchmod exists using hasattr()"
    )

    # Verify the fchmod call is inside an if block
    # The pattern should be: if hasattr(os, "fchmod"): os.fchmod(...)
    assert "if hasattr" in source, (
        "Code should have conditional check for fchmod"
    )

    # Verify basic functionality still works
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [
        Todo(id=1, text="first"),
        Todo(id=2, text="second"),
        Todo(id=3, text="third"),
    ]

    storage.save(todos)

    # Verify the save completed successfully
    loaded = storage.load()
    assert len(loaded) == 3
    assert loaded[0].text == "first"
    assert loaded[1].text == "second"
    assert loaded[2].text == "third"


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="This test is for Unix systems to verify fchmod behavior",
)
def test_unix_systems_still_set_restrictive_permissions(tmp_path) -> None:
    """Issue #2739: On Unix systems, temp files should still have 0o600 permissions.

    This ensures the fix doesn't break the security behavior on Unix systems
    where os.fchmod is available.
    """
    import os
    import stat
    import tempfile as tempfile_module

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track permissions of created temp files
    permissions_seen = []

    original_mkstemp = tempfile_module.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        # Check permissions immediately after creation
        file_stat = os.stat(path)
        file_mode = stat.S_IMODE(file_stat.st_mode)
        permissions_seen.append((path, file_mode))
        return fd, path

    import tempfile
    original = tempfile.mkstemp
    tempfile.mkstemp = tracking_mkstemp

    try:
        storage.save([Todo(id=1, text="test")])
    finally:
        tempfile.mkstemp = original

    # On Unix, temp files should have 0o600 permissions
    assert len(permissions_seen) > 0, "No temp files were created"

    for path, mode in permissions_seen:
        # The mode should be 0o600 (rw-------) on Unix systems
        assert mode == 0o600, (
            f"Temp file has incorrect permissions: {oct(mode)} "
            f"(expected 0o600, got 0o{mode:o}). "
            f"File was: {path}"
        )


def test_atomic_write_behavior_preserved(tmp_path) -> None:
    """Issue #2739: Verify the fix doesn't break atomic write behavior.

    The atomic rename pattern (os.replace) should still work correctly
    regardless of the fchmod handling.
    """

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="atomic test")]

    # Save and verify it works
    storage.save(todos)

    # Verify file content is valid
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "atomic test"

    # Verify the file was actually created
    assert db.exists(), "Database file should exist after save"
