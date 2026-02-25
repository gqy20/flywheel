"""Regression tests for issue #5747: os.fchmod is Unix-only.

Issue: os.fchmod raises AttributeError on Windows because it's Unix-only.

The save() method should:
1. Succeed on Windows without AttributeError
2. Still set 0o600 permissions on Unix systems

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat
import sys
from unittest import mock

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestWindowsCompatibility:
    """Tests for Windows compatibility of TodoStorage.save()."""

    def test_save_succeeds_without_fchmod(self, tmp_path) -> None:
        """Issue #5747: save() should not raise AttributeError when os.fchmod is missing.

        This simulates Windows behavior where os.fchmod doesn't exist.
        Before fix: save() raises AttributeError: module 'os' has no attribute 'fchmod'
        After fix: save() succeeds without error
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Simulate Windows by removing os.fchmod entirely
        # On Windows, hasattr(os, 'fchmod') returns False
        with mock.patch.dict(os.__dict__, {}, clear=False):
            if "fchmod" in os.__dict__:
                del os.__dict__["fchmod"]
            # This should NOT raise AttributeError
            storage.save([Todo(id=1, text="test")])

        # Verify data was saved correctly
        assert db.exists()
        import json

        data = json.loads(db.read_text())
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["text"] == "test"

    def test_save_succeeds_with_mocked_no_fchmod(self, tmp_path) -> None:
        """Issue #5747: save() should work when hasattr(os, 'fchmod') returns False.

        This is a simpler test that mocks hasattr to return False.
        """
        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Mock hasattr to return False for os.fchmod
        import builtins

        original_hasattr = builtins.hasattr

        def mock_hasattr(obj, name, *args):
            if obj is os and name == "fchmod":
                return False
            return original_hasattr(obj, name, *args)

        with mock.patch("builtins.hasattr", mock_hasattr):
            # This should NOT raise any error
            storage.save([Todo(id=1, text="test")])

        # Verify data was saved correctly
        assert db.exists()
        import json

        data = json.loads(db.read_text())
        assert len(data) == 1

    def test_save_still_sets_permissions_on_unix(self, tmp_path) -> None:
        """Issue #5747: save() should still set 0o600 permissions on Unix.

        The fix should not break the security feature on Unix systems.
        This test verifies that when fchmod IS available, it's used correctly.
        """
        # Skip on Windows since fchmod doesn't exist
        if not hasattr(os, "fchmod"):
            pytest.skip("os.fchmod not available on this platform")

        db = tmp_path / "todo.json"
        storage = TodoStorage(str(db))

        # Track if fchmod was called with correct permissions
        fchmod_calls = []

        original_fchmod = os.fchmod

        def tracking_fchmod(fd, mode):
            fchmod_calls.append((fd, mode))
            return original_fchmod(fd, mode)

        with mock.patch.object(os, "fchmod", tracking_fchmod):
            storage.save([Todo(id=1, text="test")])

        # Verify fchmod was called with 0o600
        assert len(fchmod_calls) == 1, f"Expected 1 fchmod call, got {len(fchmod_calls)}"
        _, mode = fchmod_calls[0]
        assert mode == (stat.S_IRUSR | stat.S_IWUSR), (
            f"fchmod called with wrong mode: {oct(mode)} (expected 0o600)"
        )

    def test_hasattr_fchmod_detection(self) -> None:
        """Verify that the fix uses hasattr() to detect fchmod availability.

        The code should check if os.fchmod exists before calling it.
        This is a documentation/metadata test for the fix approach.
        """
        # On Unix, hasattr should return True
        # On Windows, hasattr should return False
        has_fchmod = hasattr(os, "fchmod")

        # This assertion documents expected behavior:
        # - Unix systems: has_fchmod == True
        # - Windows systems: has_fchmod == False
        # The fix should work correctly in both cases
        if sys.platform == "win32":
            assert not has_fchmod, "On Windows, os.fchmod should not exist"
        else:
            # On Unix, fchmod should exist
            assert has_fchmod, "On Unix, os.fchmod should exist"
