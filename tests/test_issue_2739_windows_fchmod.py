"""Regression tests for issue #2739: os.fchmod() is not available on Windows.

Issue: os.fchmod() is only available on Unix/Linux platforms. When TodoStorage.save()
is called on Windows (or any platform where os.fchmod doesn't exist), it raises
AttributeError: module 'os' has no attribute 'fchmod'.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_when_fchmod_unavailable(tmp_path) -> None:
    """Issue #2739: TodoStorage.save() should work even when os.fchmod is unavailable.

    On Windows, os.fchmod doesn't exist. This test simulates Windows behavior by
    removing os.fchmod and verifies that save() still works correctly.

    Before fix: AttributeError: module 'os' has no attribute 'fchmod'
    After fix: save() completes successfully using os.chmod as fallback
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test on simulated Windows")]

    # Simulate Windows environment where os.fchmod doesn't exist
    # We need to delete the attribute, not just patch it
    import flywheel.storage as storage_module
    original_fchmod = storage_module.os.fchmod

    # Delete fchmod to simulate Windows
    delattr(storage_module.os, "fchmod")

    try:
        # This should NOT raise AttributeError
        storage.save(todos)

        # Verify the data was saved correctly
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test on simulated Windows"
    finally:
        # Restore fchmod for other tests
        storage_module.os.fchmod = original_fchmod


def test_save_with_hasattr_fchmod_check(tmp_path) -> None:
    """Issue #2739: Test that hasattr check properly detects fchmod availability."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    todos = [Todo(id=1, text="test hasattr check")]

    # Simulate Windows environment where os.fchmod doesn't exist
    import flywheel.storage as storage_module
    original_fchmod = storage_module.os.fchmod
    delattr(storage_module.os, "fchmod")

    try:
        # Verify hasattr returns False
        assert not hasattr(storage_module.os, "fchmod")

        # This should NOT raise AttributeError
        storage.save(todos)

        # Verify the data was saved correctly
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "test hasattr check"
    finally:
        # Restore fchmod for other tests
        storage_module.os.fchmod = original_fchmod


def test_multiple_saves_work_without_fchmod(tmp_path) -> None:
    """Issue #2739: Multiple consecutive saves should work without fchmod."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate Windows environment by removing fchmod
    import flywheel.storage as storage_module
    original_fchmod = storage_module.os.fchmod
    delattr(storage_module.os, "fchmod")

    try:
        # First save
        storage.save([Todo(id=1, text="first")])

        # Second save
        storage.save([Todo(id=1, text="second"), Todo(id=2, text="another")])

        # Third save with modification
        storage.save([Todo(id=1, text="third", done=True)])

        # Verify final state
        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].text == "third"
        assert loaded[0].done is True
    finally:
        # Restore fchmod for other tests
        storage_module.os.fchmod = original_fchmod
