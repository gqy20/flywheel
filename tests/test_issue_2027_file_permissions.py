"""Regression tests for issue #2027: File permissions discrepancy.

Issue: Comment states 0o600 but code sets 0o700 (S_IRWXU includes execute permission).

The fix should:
1. Set exact 0o600 (rw-------) permissions, not 0o700 (rwx------)
2. Update comment to match implementation
3. Ensure no execute bit is set on temp files
"""

from __future__ import annotations

import os
import stat
from unittest.mock import patch

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_temp_file_has_exact_0o600_permissions(tmp_path) -> None:
    """Issue #2027: Temp file should have exactly mode 0o600 (owner read/write only).

    Before fix: Code uses stat.S_IRWXU which is 0o700 (rwx------)
    After fix: Code should use stat.S_IRUSR | stat.S_IWUSR which is 0o600 (rw-------)

    The test FAILS when execute bit is set and PASSES when permissions are exactly 0o600.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track fchmod calls to verify the exact permissions being set
    fchmod_calls = []

    original_fchmod = os.fchmod

    def tracking_fchmod(fd, mode):
        fchmod_calls.append(mode)
        return original_fchmod(fd, mode)

    with patch("os.fchmod", side_effect=tracking_fchmod):
        storage.save([Todo(id=1, text="test")])

    # Verify fchmod was called with exactly 0o600 permissions
    assert len(fchmod_calls) > 0, "fchmod was not called"

    for mode in fchmod_calls:
        # Should be exactly 0o600 (rw-------)
        assert mode == 0o600, (
            f"Temp file permissions are incorrect: {oct(mode)}. "
            f"Expected exactly 0o600 (rw-------), got {oct(mode)}. "
            f"stat.S_IRWXU (0o700) includes execute permission which is not needed for data files."
        )


def test_temp_file_has_no_execute_bit(tmp_path) -> None:
    """Issue #2027: Temp file should NOT have execute permission set.

    Data files should never have execute permission as it:
    1. Creates unnecessary security surface
    2. Does not match documented behavior (0o600)
    3. Violates principle of least privilege
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Track fchmod calls to check if execute bit is set
    execute_bit_seen = []

    original_fchmod = os.fchmod

    def tracking_fchmod(fd, mode):
        # Check if execute bit is set for owner
        has_execute = bool(mode & stat.S_IXUSR)
        execute_bit_seen.append(has_execute)
        return original_fchmod(fd, mode)

    with patch("os.fchmod", side_effect=tracking_fchmod):
        storage.save([Todo(id=1, text="test")])

    # No fchmod call should set execute bit
    assert len(execute_bit_seen) > 0, "fchmod was not called"
    for has_execute in execute_bit_seen:
        assert not has_execute, (
            "Temp file has execute bit set (stat.S_IXUSR). "
            "Data files should not have execute permission. "
            "Use stat.S_IRUSR | stat.S_IWUSR for 0o600 instead of stat.S_IRWXU for 0o700."
        )


def test_docstring_promises_0o600_matches_reality(tmp_path) -> None:
    """Issue #2027: Verify the implementation matches the documented behavior.

    The docstring in TodoStorage.save() promises 0o600 permissions.
    This test verifies that the actual code delivers what's promised.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    fchmod_calls = []

    original_fchmod = os.fchmod

    def tracking_fchmod(fd, mode):
        fchmod_calls.append(mode)
        return original_fchmod(fd, mode)

    with patch("os.fchmod", side_effect=tracking_fchmod):
        storage.save([Todo(id=1, text="test")])

    # The docstring says "restrictive permissions (0o600)"
    # Let's verify the implementation actually uses 0o600
    assert len(fchmod_calls) > 0, "fchmod was not called"
    for mode in fchmod_calls:
        # Check for promised 0o600 permissions
        assert mode == 0o600, (
            f"Implementation mismatch: docstring promises 0o600, got {oct(mode)}. "
            f"Update code to use stat.S_IRUSR | stat.S_IWUSR for exact 0o600 permissions."
        )


def test_comment_matches_implementation(tmp_path) -> None:
    """Issue #2027: Verify comment matches the actual permissions code.

    The comment at line 112 says "we'll tighten to 0o600" but uses stat.S_IRWXU.
    This test verifies that the code actually does what the comment promises.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    fchmod_calls = []

    original_fchmod = os.fchmod

    def tracking_fchmod(fd, mode):
        fchmod_calls.append(mode)
        return original_fchmod(fd, mode)

    with patch("os.fchmod", side_effect=tracking_fchmod):
        storage.save([Todo(id=1, text="test")])

    # The comment promises "we'll tighten to 0o600"
    # stat.S_IRWXU is 0o700, not 0o600
    # stat.S_IRUSR | stat.S_IWUSR is 0o600
    assert len(fchmod_calls) > 0, "fchmod was not called"
    for mode in fchmod_calls:
        # Verify the code actually uses 0o600, not 0o700
        assert mode == 0o600, (
            f"Comment says 'we'll tighten to 0o600' but code uses {oct(mode)}. "
            f"Replace stat.S_IRWXU with stat.S_IRUSR | stat.S_IWUSR."
        )
        # Verify we're not using S_IRWXU (which includes execute bit)
        assert mode != stat.S_IRWXU, (
            "Code uses stat.S_IRWXU (0o700) but comment says 'we'll tighten to 0o600'. "
            "Update the code to use stat.S_IRUSR | stat.S_IWUSR."
        )
