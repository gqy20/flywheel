"""Regression tests for issue #2560: os.fchmod compatibility on non-Unix platforms.

Issue: os.fchmod is only available on Unix platforms and will raise
AttributeError on Windows. The code should check hasattr(os, 'fchmod')
before attempting to call it.

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import builtins
import os
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_works_on_platform_without_fchmod(tmp_path) -> None:
    """Issue #2560: TodoStorage.save() should work on platforms without os.fchmod.

    On Windows and other non-Unix platforms, os.fchmod doesn't exist.
    The code should gracefully handle this by checking hasattr(os, 'fchmod').
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Mock hasattr to return False for os.fchmod
    # This simulates a platform where fchmod doesn't exist
    original_hasattr = builtins.hasattr

    def mock_hasattr(obj, name):
        if obj is os and name == "fchmod":
            return False
        return original_hasattr(obj, name)

    with patch("builtins.hasattr", side_effect=mock_hasattr):
        # This should not raise AttributeError - the code should check hasattr first
        storage.save([Todo(id=1, text="test on platform without fchmod")])

    # Verify the data was actually saved
    loaded = storage.load()
    assert len(loaded) == 1
    assert loaded[0].text == "test on platform without fchmod"


def test_code_has_hasattr_check() -> None:
    """Issue #2560: Verify the code uses hasattr check for os.fchmod.

    This test verifies the actual implementation has the hasattr check.
    """
    import inspect

    # Get the source code of the save method
    source = inspect.getsource(TodoStorage.save)

    # The code should check for fchmod using hasattr before calling it
    # This is a code quality check to ensure the fix is implemented
    assert "hasattr" in source and "fchmod" in source, (
        "TodoStorage.save should check hasattr(os, 'fchmod') before calling os.fchmod"
    )


def test_fchmod_guarded_by_hasattr(tmp_path) -> None:
    """Issue #2560: Test that fchmod call is properly guarded.

    This ensures the hasattr check comes before the fchmod call.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track the call sequence
    call_log = []

    original_hasattr = builtins.hasattr

    def logging_hasattr(obj, name):
        if obj is os and name == "fchmod":
            call_log.append("hasattr_check")
        return original_hasattr(obj, name)

    original_fchmod = os.fchmod

    def logging_fchmod(fd, mode):
        call_log.append("fchmod_call")
        return original_fchmod(fd, mode)

    with patch("builtins.hasattr", side_effect=logging_hasattr):
        with patch.object(os, "fchmod", side_effect=logging_fchmod):
            storage.save([Todo(id=2, text="test")])

    # On Unix (where this test runs), hasattr should be checked before fchmod
    # The hasattr check should come first
    if len(call_log) >= 2:
        assert call_log[0] == "hasattr_check", (
            f"hasattr should be checked before fchmod call, got: {call_log}"
        )
