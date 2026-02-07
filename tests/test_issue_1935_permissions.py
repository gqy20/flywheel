"""Regression test for issue #1935: Atomic save should use minimal permissions.

This test verifies that temp files created during atomic save have the most
restrictive permissions possible (0o600 - owner read/write only), not execute.

The current implementation uses 0o700 (rwx------) which grants unnecessary
execute permission to the temp file. This test patches os.fchmod to verify
the actual permission value being set.

Test plan:
- Normal save should set temp file permissions to 0o600
"""
from __future__ import annotations

import os
import stat
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_temp_file_uses_0600_not_0700(tmp_path) -> None:
    """Issue #1935: Temp file should use 0o600, not 0o700.

    The temp file stores JSON data and doesn't need execute permission.
    Using 0o600 instead of 0o700 follows the principle of least privilege.

    Current code uses stat.S_IRWXU (0o700) but should use 0o600.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track what mode is actually passed to os.fchmod
    fchmod_modes = []

    original_fchmod = os.fchmod

    def tracking_fchmod(fd, mode):
        fchmod_modes.append(mode)
        return original_fchmod(fd, mode)

    with patch("flywheel.storage.os.fchmod", tracking_fchmod):
        storage.save([Todo(id=1, text="test")])

    # Verify os.fchmod was called
    assert len(fchmod_modes) > 0, "os.fchmod should have been called"

    # The mode should be 0o600 (rw-------), not 0o700 (rwx------)
    mode = fchmod_modes[0]
    assert mode == 0o600, (
        f"Temp file should use 0o600 permissions (rw-------), "
        f"not 0o700 (rwx------). Got {oct(mode)}"
    )

    # Verify no execute permission is set
    assert mode & stat.S_IXUSR == 0, (
        f"Temp file should not have execute permission. Got {oct(mode)}"
    )

    # Verify read and write are set
    assert mode & stat.S_IRUSR != 0, "Owner read permission should be set"
    assert mode & stat.S_IWUSR != 0, "Owner write permission should be set"
